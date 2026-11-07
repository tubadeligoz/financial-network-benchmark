from contextlib import asynccontextmanager
import csv
import io
import json
import os
from pathlib import Path
import uuid

from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.algorithms import AlgorithmEngine
from app.api.jobs import Jobs
from app.api.repository import Repository, read_json
from app.api.schemas import AlgorithmRequest, BenchmarkRequest, StressRequest
from app.datasets.financial import validate_financial_graph
from app.benchmark.config import validate_config


def create_app(root=None):
    root=Path(root or os.environ.get('FNB_PROJECT_ROOT',Path(__file__).resolve().parents[3])).resolve()
    repo=Repository(root);jobs=Jobs(root);engine=AlgorithmEngine()
    @asynccontextmanager
    async def lifespan(app):
        jobs.start()
        yield
        jobs.close()
    app=FastAPI(title='Financial Network Benchmark',version='0.5.0',lifespan=lifespan)
    app.state.repository=repo;app.state.jobs=jobs
    origins=['http://127.0.0.1:5173','http://localhost:5173','http://127.0.0.1:8000',
             'http://localhost:8000','http://127.0.0.1:4173','http://localhost:4173']
    app.add_middleware(CORSMiddleware,allow_origins=origins,allow_methods=['GET','POST'],
                       allow_headers=['Content-Type','X-FNB-Client'])
    app.add_middleware(TrustedHostMiddleware,allowed_hosts=['localhost','127.0.0.1','testserver'])

    @app.middleware('http')
    async def local_mutations(request: Request,call_next):
        if request.method=='POST':
            if request.headers.get('x-fnb-client')!='local-web' or request.headers.get('origin') not in (None,*origins):
                return JSONResponse(status_code=403,content={'detail':'Local application header/origin required.'})
            length=request.headers.get('content-length')
            try: size=int(length) if length else 0
            except ValueError: return JSONResponse(status_code=400,content={'detail':'Invalid Content-Length.'})
            if size<0: return JSONResponse(status_code=400,content={'detail':'Invalid Content-Length.'})
            if size>65536 or len(await request.body())>65536:
                return JSONResponse(status_code=413,content={'detail':'Request exceeds 64 KiB. File upload is not enabled.'})
        return await call_next(request)

    @app.exception_handler(KeyError)
    async def missing(request,exc): return JSONResponse(status_code=404,content={'detail':str(exc.args[0])})
    @app.exception_handler(ValueError)
    async def invalid(request,exc): return JSONResponse(status_code=422,content={'detail':str(exc)})

    @app.get('/api/v1/health')
    def health(): return dict(status='ok',mode='local_research',uploads_enabled=False)

    @app.get('/api/v1/datasets')
    def datasets(): return repo.datasets()

    @app.get('/api/v1/datasets/{dataset}')
    def dataset_detail(dataset: str):
        entry=next((d for d in repo.datasets() if d['id']==dataset),None)
        if not entry: raise KeyError('Dataset not found.')
        return entry

    @app.get('/api/v1/datasets/{dataset}/periods')
    def periods(dataset: str): return dataset_detail(dataset)['periods']

    @app.get('/api/v1/datasets/{dataset}/periods/{period}/validation')
    def validation(dataset: str,period: str): return repo.get(dataset,period)[2]

    @app.get('/api/v1/datasets/{dataset}/periods/{period}/statistics')
    def stats(dataset: str,period: str,summary: bool=False):
        values=repo.get(dataset,period)[1]
        if not summary: return values
        return {k:({sub:val for sub,val in v.items() if sub not in ('members','sorted_values')}
                   if isinstance(v,dict) else v)
                for k,v in values.items() if k!='nodes'} | {'statistics_scope':'summary'}

    @app.get('/api/v1/datasets/{dataset}/periods/{period}/analyses')
    def analyses(dataset: str,period: str):
        g,_,_=repo.get(dataset,period)
        return repo.analyses(g.graph['graph_sha256'])

    @app.get('/api/v1/datasets/{dataset}/periods/{period}/search')
    def search(dataset: str,period: str,q: str=Query('',max_length=80)):
        g,_,_=repo.get(dataset,period)
        return [dict(node_id=n,name=a.get('source_metadata',{}).get('country_name',n))
            for n,a in sorted(g.nodes(data=True)) if q.lower() in n.lower() or
            q.lower() in a.get('source_metadata',{}).get('country_name','').lower()][:20]

    @app.get('/api/v1/datasets/{dataset}/periods/{period}/graph')
    def graph(dataset: str,period: str,limit_nodes: int=Query(60,ge=1,le=250),
              min_exposure: float=Query(0,ge=0,allow_inf_nan=False),focus: str|None=None):
        g,s,_=repo.get(dataset,period)
        if focus is not None and focus not in g: raise KeyError('Node not found in selected graph.')
        order=lambda n:(-s['nodes'][n]['in_strength']-s['nodes'][n]['out_strength'],n)
        if focus:
            candidates=set(g.predecessors(focus))|set(g.successors(focus))
            nodes=[focus]+sorted(candidates-{focus},key=order)[:limit_nodes-1]
        else: nodes=sorted(g,key=order)[:limit_nodes]
        chosen=set(nodes)
        eligible=[(u,v,a) for u,v,a in g.edges(data=True) if u in chosen and v in chosen and a['exposure']>=min_exposure]
        eligible.sort(key=lambda x:(-x[2]['exposure'],x[0],x[1]))
        edges=eligible[:400]
        return dict(graph_sha256=g.graph['graph_sha256'],period=period,
            total_nodes=len(g),total_edges=g.number_of_edges(),visible_nodes=len(nodes),visible_edges=len(edges),
            filtered=len(nodes)<len(g) or len(edges)<g.number_of_edges(),
            filter_description='Top strength nodes or focused neighbors; minimum exposure; highest 400 visible edges.',
            analysis_scope='full_validated_graph',exposure_unit=g.graph['exposure_unit'],
            nodes=[dict(id=n,label=n,name=g.nodes[n].get('source_metadata',{}).get('country_name',n),**s['nodes'][n]) for n in nodes],
            edges=[dict(id=f'{u}:{v}',source=u,target=v,exposure=a['exposure']) for u,v,a in edges])

    @app.get('/api/v1/datasets/{dataset}/periods/{period}/nodes/{node}')
    def node_detail(dataset: str,period: str,node: str):
        g,s,_=repo.get(dataset,period)
        if node not in g: raise KeyError('Node not found.')
        results=repo.analyses(g.graph['graph_sha256'])
        scores={aid:next((r['score'] for r in result['scores'] if r['node_id']==node),None) for aid,result in results.items()}
        connections=sorted([(u,v,a) for u,v,a in g.in_edges(node,data=True)]+
            [(u,v,a) for u,v,a in g.out_edges(node,data=True)],key=lambda x:(-x[2]['exposure'],x[0],x[1]))
        return dict(node_id=node,attributes=g.nodes[node],statistics=s['nodes'][node],scores=scores,
            exposure_unit=g.graph['exposure_unit'],graph_sha256=g.graph['graph_sha256'],
            neighbors=sorted(set(g.predecessors(node))|set(g.successors(node))),
            connections=[dict(source=u,target=v,exposure=a['exposure']) for u,v,a in connections[:100]],
            total_connections=len(connections))

    @app.get('/api/v1/algorithms')
    def algorithms(): return engine.catalog()

    @app.get('/api/v1/datasets/{dataset}/periods/{period}/financial-eligibility')
    def eligibility(dataset: str,period: str):
        g,_,_=repo.get(dataset,period)
        try: validate_financial_graph(g)
        except ValueError as exc: return dict(eligible=False,reason=str(exc),banks=[],assumptions=None)
        return dict(eligible=True,reason='SYNTHETIC — NOT CALIBRATED TO BIS',
            banks=[dict(node_id=n,**a['available_financial_features']) for n,a in sorted(g.nodes(data=True))],
            assumptions=g.graph['financial_model'])

    @app.post('/api/v1/stress-tests',status_code=202)
    def stress(body: StressRequest):
        if (len(set(body.periods))!=len(body.periods) or len(set(body.shocked_nodes))!=len(body.shocked_nodes)
                or len(set(body.shock_magnitudes))!=len(body.shock_magnitudes)):
            raise ValueError('Duplicate periods, shock nodes or magnitudes are not allowed.')
        sources=[]
        for period in body.periods:
            g,_,_=repo.get(body.dataset,period)
            for magnitude in body.shock_magnitudes:
                p=engine.resolve_parameters('debtrank',dict(initial_shocks={n:magnitude for n in body.shocked_nodes}))
                engine._algorithms['debtrank'].validate_graph_parameters(g,p)
            sources.append(dict(source=repo.source(body.dataset,period),graph_sha256=g.graph['graph_sha256']))
        return jobs.submit('stress',dict(dataset=body.dataset,sources=sources,
            shocked_nodes=body.shocked_nodes,shock_magnitudes=body.shock_magnitudes))

    @app.get('/api/v1/stress-experiments')
    def stress_experiments(dataset: str|None=None):
        records=[read_json(p) for p in sorted((repo.web/'stress').glob('stress-*.json'),key=lambda p:p.stat().st_mtime,reverse=True)]
        return [r for r in records if r and (dataset is None or r['dataset_key']==dataset)]

    @app.get('/api/v1/stress-experiments/{experiment_id}/export')
    def stress_export(experiment_id: str,format: str=Query('json',pattern='^(json|csv)$')):
        suite=next((s for s in stress_experiments() if s['id']==experiment_id),None)
        if not suite: raise KeyError('Stress experiment not found.')
        if format=='json':
            content=json.dumps(suite,ensure_ascii=False,allow_nan=False);mime='application/json'
        else:
            buffer=io.StringIO();writer=csv.writer(buffer)
            writer.writerow(['experiment_id','dataset_id','dataset_version','period','graph_sha256','model_id','mode','parameters','model_assumptions','node_id','risk_score','rank','status'])
            for r in suite['scenarios']+suite['impact_rankings']:
                for score in r['scores']:
                    writer.writerow([suite['id'],r['dataset_id'],r['dataset_version'],r['period'],r['graph_sha256'],r['metadata']['model_id'],r['parameters']['mode'],json.dumps(r['parameters']),json.dumps(r['metadata']['model_assumptions']),score['node_id'],score['score'],score['rank'],r['status']])
            content=buffer.getvalue();mime='text/csv'
        return Response(content,media_type=mime,headers={'Content-Disposition':f'attachment; filename="{experiment_id}.{format}"'})

    @app.post('/api/v1/analyses',status_code=202)
    def run_analysis(body: AlgorithmRequest):
        g,_,_=repo.get(body.dataset,body.period)
        parameters=engine.resolve_parameters(body.algorithm_id,body.parameters)
        engine._algorithms[body.algorithm_id].validate_graph_parameters(g,parameters)
        return jobs.submit('algorithm',dict(source=repo.source(body.dataset,body.period),
            algorithm_id=body.algorithm_id,parameters=parameters,expected_graph_sha256=g.graph['graph_sha256']))

    @app.post('/api/v1/benchmarks',status_code=202)
    def benchmark(body: BenchmarkRequest):
        g,_,_=repo.get(body.dataset,body.period)
        for case in body.algorithms:
            parameters=engine.resolve_parameters(case.algorithm_id,case.parameters)
            engine._algorithms[case.algorithm_id].validate_graph_parameters(g,parameters)
        config=validate_config(dict(experiment_id='web-'+uuid.uuid4().hex[:16],
            source=repo.source(body.dataset,body.period),algorithms=[c.model_dump() for c in body.algorithms],
            repeat_count=body.repeat_count,random_seed=body.random_seed,warmup_count=1,
            timeout=dict(trial_seconds=body.algorithm_timeout_seconds+30,algorithm_seconds=body.algorithm_timeout_seconds),
            measurement=dict(memory_repeats=body.repeat_count,sample_interval_ms=5,rss_limit_mb=2048),
            expected_graph={'graph_sha256':g.graph['graph_sha256']}))
        return jobs.submit('benchmark',dict(config=config))

    @app.get('/api/v1/jobs/{job_id}')
    def job(job_id: str): return jobs.get(job_id)

    @app.post('/api/v1/jobs/{job_id}/cancel')
    def cancel(job_id: str): return jobs.cancel(job_id)

    @app.get('/api/v1/experiments')
    def experiments():
        return [dict(id=r['id'],**r['summary']) for r in repo.experiments()]

    @app.get('/api/v1/experiments/{experiment_id}')
    def results(experiment_id: str,top: int=Query(20,ge=1,le=100)):
        return repo.results(experiment_id,top)

    @app.get('/api/v1/experiments/{experiment_id}/export')
    def export(experiment_id: str,format: str=Query('json',pattern='^(json|csv)$')):
        item=repo.experiment(experiment_id)
        if format=='json':
            payload=repo.results(experiment_id,100)
            payload['raw_measurements']=read_json(item['path']/'raw-measurements.json')
            payload['rankings']={p.stem:read_json(p) for p in (item['path']/'rankings').glob('*.json')}
            text=json.dumps(payload,ensure_ascii=False,allow_nan=False)
            mime='application/json'
        else:
            buffer=io.StringIO();writer=csv.writer(buffer)
            writer.writerow(['case_id','algorithm_id','dataset_id','dataset_version','period','graph_sha256','node_id','score','rank'])
            for file in (item['path']/'rankings').glob('*.json'):
                result=read_json(file)
                if not result: continue
                for row in result['scores']:
                    writer.writerow([file.stem,result['algorithm_id'],result['dataset_id'],result['dataset_version'],
                        result['period'],result['graph_sha256'],row['node_id'],row['score'],row['rank']])
            text=buffer.getvalue();mime='text/csv'
        return Response(text,media_type=mime,headers={'Content-Disposition':f'attachment; filename="{experiment_id}.{format}"'})

    @app.get('/api/v1/analysis/scalability')
    def scalability():
        rows=[];seen=set()
        for item in repo.experiments():
            s=item['summary']
            if s['graph']['data_kind']!='synthetic': continue
            key=s['experiment_id']
            if key in seen: continue
            seen.add(key)
            for case,a in s['aggregated'].items():
                rows.append(dict(experiment_id=item['id'],dataset=s['graph']['dataset_id'],
                    node_count=s['graph']['node_count'],edge_count=s['graph']['edge_count'],case_id=case,
                    median_seconds=a['runtime_seconds']['median'],timing_successes=a['timing_successes'],status=s['status']))
        return rows

    @app.get('/api/v1/analysis/temporal')
    def temporal():
        paths=sorted((root/'experiments/temporal').glob('*.json'),key=lambda p:p.stat().st_mtime,reverse=True)
        return read_json(paths[0]) if paths else {'pairs':[]}

    dist=root/'frontend/dist'
    if dist.exists(): app.mount('/',StaticFiles(directory=dist,html=True),name='web')
    return app


app=create_app()
