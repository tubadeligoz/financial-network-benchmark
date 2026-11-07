import { useCallback,useState } from 'react';
import { Database, Network, FlaskConical, ChartNoAxesCombined, Moon, Sun, Menu, X, ArrowUpRight } from 'lucide-react';
import type { Dataset, Page } from './api/types';
import { useResource } from './hooks/useResource';
import { Status } from './components/States';
import { Datasets } from './pages/Datasets';
import { Explorer } from './pages/Explorer';
import { Benchmarks } from './pages/Benchmarks';
import { Results } from './pages/Results';

const navigation = [ ['datasets', 'Datasets', Database], ['explorer', 'Graph Explorer', Network], ['benchmarks', 'Benchmarks', FlaskConical], ['results', 'Results & Analysis', ChartNoAxesCombined] ] as const;
export interface Context { dataset: string; period: string; revision: number }
export default function App() {
  const resource = useResource<Dataset[]>('/datasets');
  const [selection, setSelection] = useState({ dataset: 'bis-lbs', period: '2025-Q4' });
  const [page, setPage] = useState<Page>('datasets');
  const [mobile, setMobile] = useState(false);
  const [dark, setDark] = useState(() => localStorage.getItem('fnb-theme') === 'dark');
  const [revision, setRevision] = useState(0);
  const refresh=useCallback(()=>setRevision(v=>v+1),[]);
  const [node, setNode] = useState('');
  const [experiment, setExperiment] = useState('');
  const datasets = resource.data ?? [];
  const selected = datasets.find(d => d.id === selection.dataset) ?? datasets[0];
  const period = selected?.periods.find(p => p.period === selection.period)?.period ?? selected?.periods[0]?.period ?? '';
  const context = { dataset: selected?.id ?? '', period, revision };
  const go = (next: Page) => { setPage(next); setMobile(false); };
  const openResults = (id: string) => { setExperiment(id); go('results'); };
  const openNode = (dataset: string, period: string, id: string) => { setSelection({dataset, period}); setNode(id); go('explorer'); };
  return <div className={`app ${dark ? 'dark' : ''}`}>
    {mobile && <button className="backdrop" aria-label="Close navigation" onClick={() => setMobile(false)} />}
    <aside className={`sidebar ${mobile ? 'open' : ''}`}>
      <a className="brand" href="#" onClick={e => { e.preventDefault(); go('datasets'); }}><Network size={30}/><span>FINANCIAL<br/><b>NETWORK LAB</b></span></a>
      <div className="nav-label">RESEARCH WORKSPACE</div>
      <nav aria-label="Main navigation">{navigation.map(([id,label,Icon]) => <button key={id} className={page === id ? 'active' : ''} aria-current={page === id ? 'page' : undefined} onClick={() => go(id)}><Icon size={19}/>{label}{page === id && <span className="nav-dot"/>}</button>)}</nav>
      <div className="sidebar-note"><span className="live-dot"/> LOCAL RESEARCH INSTANCE<p>Traceable data.<br/>Reproducible analysis.</p><small>PLATFORM / 0.5.0</small></div>
    </aside>
    <div className="workspace">
      <header className="topbar"><button className="icon-button mobile-toggle" aria-label="Toggle navigation" aria-expanded={mobile} onClick={() => setMobile(!mobile)}>{mobile ? <X/> : <Menu/>}</button><span className="breadcrumb">Workspace <span>/</span> {navigation.find(n => n[0] === page)?.[1]}</span>
        <div className="selection"><label>Dataset<select aria-label="Dataset" value={selected?.id ?? ''} onChange={e => { const d = datasets.find(d => d.id === e.target.value)!; setNode(''); setSelection({dataset:d.id, period:d.periods[0]?.period ?? ''}); }}>{datasets.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}</select></label><label>Period<select aria-label="Period" value={period} onChange={e => { setNode(''); setSelection({dataset:selected.id,period:e.target.value}); }}>{selected?.periods.map(p => <option key={p.period}>{p.period}</option>)}</select></label></div>
        <button className="icon-button" aria-label={dark ? 'Use light theme' : 'Use dark theme'} onClick={() => { localStorage.setItem('fnb-theme',dark ? 'light':'dark'); setDark(!dark); }}>{dark ? <Sun size={19}/> : <Moon size={19}/>}</button>
      </header>
      <main><Status loading={resource.loading} error={resource.error} empty={!resource.loading && !resource.error && !selected ? 'No registered datasets. Add validated local source files and restart the API.' : undefined}>
        {selected && <><div className="eyebrow">FINANCIAL NETWORK BENCHMARK <span> / PHASE 05</span></div>
          {page === 'datasets' && <Datasets datasets={datasets} selected={selected} context={context} choose={(dataset,period) => setSelection({dataset,period})} explore={() => go('explorer')}/>}
          {page === 'explorer' && <Explorer key={`${context.dataset}/${context.period}`} context={context} initialNode={node} refresh={refresh}/>}
          {page === 'benchmarks' && <Benchmarks key={`${context.dataset}/${context.period}`} context={context} onResults={openResults}/>}
          {page === 'results' && <Results context={context} experimentId={experiment} onExperiment={setExperiment} openNode={openNode}/>}
        </>}
      </Status></main>
      <footer><span>Financial Network Benchmark · Research infrastructure</span><a href="/docs" target="_blank" rel="noreferrer">API reference <ArrowUpRight size={13}/></a></footer>
    </div>
  </div>;
}
