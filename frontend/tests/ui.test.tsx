import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../src/App';
import { Benchmarks } from '../src/pages/Benchmarks';
import { Status, JobStatus } from '../src/components/States';
import { api, fmt } from '../src/api/client';
import { datasets, queued, financialEligibility } from './synthetic-fixtures';
import { StressAnalysis } from '../src/components/StressAnalysis';
afterEach(()=>{cleanup();vi.unstubAllGlobals();vi.restoreAllMocks();});
describe('research UI contracts',()=>{
  it('shows loading, empty and errors without inventing results',()=>{
    const view=render(<Status loading/>);expect(screen.getByRole('status')).toHaveTextContent('Loading');
    view.rerender(<Status empty="No experiments recorded."/>);expect(screen.getByText('No experiments recorded.')).toBeVisible();
    view.rerender(<Status error="Source file unavailable"/>);expect(screen.getByRole('alert')).toHaveTextContent('Source file unavailable');
    expect(fmt(null)).toBe('Not calculated');expect(fmt(0)).toBe('0');
  });
  it('keeps actual job statuses, progress and result links',async()=>{
    const onResults=vi.fn();const view=render(<JobStatus job={queued}/>);expect(screen.getByRole('status')).toHaveTextContent('Job queued');
    view.rerender(<JobStatus job={{...queued,status:'running',progress:{message:'5/10 trials',completed:5,total:10}}}/>);expect(screen.getByRole('progressbar')).toHaveAttribute('value','5');
    view.rerender(<JobStatus job={{...queued,status:'completed',result:{experiment_id:'synthetic-result'}}} onResults={onResults}/>);
    await userEvent.click(screen.getByRole('button',{name:'View results'}));expect(onResults).toHaveBeenCalledWith('synthetic-result');
    view.rerender(<JobStatus job={{...queued,status:'failed',error:'Controlled test failure'}}/>);expect(screen.getByRole('status')).toHaveTextContent('Controlled test failure');
  });
  it('selects dataset and period, supports navigation and theme',async()=>{
    vi.stubGlobal('fetch',vi.fn(async (url:string)=>new Response(JSON.stringify(url.endsWith('/datasets')?datasets:{}),{status:200})));
    render(<App/>);expect(await screen.findByRole('heading',{name:'Start with the evidence.'})).toBeVisible();
    expect(screen.getByRole('combobox',{name:'Dataset'})).toHaveValue('synthetic-demo');
    await userEvent.selectOptions(screen.getByRole('combobox',{name:'Period'}),'2025-Q3');expect(screen.getByRole('combobox',{name:'Period'})).toHaveValue('2025-Q3');
    await userEvent.click(screen.getByRole('button',{name:'Benchmarks'}));expect(screen.getByRole('heading',{name:'Measure. Compare. Reproduce.'})).toBeVisible();
    await userEvent.click(screen.getByRole('button',{name:'Use dark theme'}));expect(screen.getByRole('button',{name:'Use light theme'})).toBeVisible();
  });
  it('submits selected methods and parameters to the actual API contract',async()=>{
    const fetch=vi.fn<(url:string,options?:RequestInit)=>Promise<Response>>().mockImplementation(async()=>new Response(JSON.stringify(queued),{status:202}));vi.stubGlobal('fetch',fetch);
    render(<Benchmarks context={{dataset:'synthetic-demo',period:'2025-Q4',revision:0}} onResults={vi.fn()}/>);
    await userEvent.click(screen.getByRole('checkbox',{name:/Unweighted betweenness/}));
    await userEvent.click(screen.getByRole('checkbox',{name:/Weighted PageRank/}));
    await userEvent.selectOptions(screen.getByRole('combobox',{name:'Repeat count'}),'10');
    await userEvent.click(screen.getByRole('button',{name:'Run benchmark'}));
    await waitFor(()=>expect(fetch).toHaveBeenCalled());
    const call=fetch.mock.calls.find(c=>String(c[0]).endsWith('/benchmarks')) as unknown as [string,RequestInit];
    const body=JSON.parse(String(call[1].body)) as {algorithms:{algorithm_id:string}[];repeat_count:number};
    expect(body.algorithms.map(a=>a.algorithm_id)).toEqual(['strength']);expect(body.repeat_count).toBe(10);
  });
  it('surfaces backend error detail',async()=>{vi.stubGlobal('fetch',vi.fn(async()=>new Response(JSON.stringify({detail:'Invalid selected period'}),{status:422})));await expect(api('/datasets')).rejects.toThrow('Invalid selected period');});
  it('submits explicit synthetic multi-bank and multi-magnitude stress assumptions',async()=>{
    const fetch=vi.fn<(url:string,options?:RequestInit)=>Promise<Response>>().mockImplementation(async(url)=>new Response(JSON.stringify(url.includes('financial-eligibility')?financialEligibility:url.includes('stress-experiments')?[]:queued),{status:200}));
    vi.stubGlobal('fetch',fetch);render(<StressAnalysis configure context={{dataset:'synthetic-bank-stress',period:'synthetic-T0',revision:0}}/>);
    await userEvent.click(await screen.findByRole('checkbox',{name:'SYN-BANK-B'}));
    await userEvent.clear(screen.getByLabelText('Shock magnitudes'));
    await userEvent.click(screen.getByRole('button',{name:'Run stress scenarios'}));
    expect(screen.getByRole('alert')).toHaveTextContent('blank values are not zero');
    expect(fetch.mock.calls.some(c=>String(c[0]).endsWith('/stress-tests'))).toBe(false);
    await userEvent.type(screen.getByLabelText('Shock magnitudes'),'0.1, 0.5');
    await userEvent.click(screen.getByRole('button',{name:'Run stress scenarios'}));
    const call=fetch.mock.calls.find(c=>String(c[0]).endsWith('/stress-tests'));
    expect(call).toBeTruthy();const body=JSON.parse(String(call![1]?.body)) as {periods:string[];shocked_nodes:string[];shock_magnitudes:number[]};
    expect(body.periods).toEqual(['synthetic-T0','synthetic-T1']);expect(body.shocked_nodes).toEqual(['SYN-BANK-C','SYN-BANK-B']);expect(body.shock_magnitudes).toEqual([.1,.5]);
  });
});
