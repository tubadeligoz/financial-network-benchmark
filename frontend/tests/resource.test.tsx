import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,renderHook,waitFor} from '@testing-library/react';
import {useResource} from '../src/hooks/useResource';
afterEach(()=>{cleanup();vi.unstubAllGlobals();});
it('never presents a previous dataset or revision as a new resource',async()=>{
  vi.stubGlobal('fetch',vi.fn((url:string)=>url.endsWith('/first')?Promise.resolve(new Response(JSON.stringify({dataset:'SYNTHETIC-FIRST'}))):new Promise(()=>{})));
  const {result,rerender}=renderHook(({path,revision})=>useResource<{dataset:string}>(path,revision),{initialProps:{path:'/first',revision:0}});
  await waitFor(()=>expect(result.current.data?.dataset).toBe('SYNTHETIC-FIRST'));
  rerender({path:'/second',revision:0});expect(result.current.data).toBeNull();expect(result.current.loading).toBe(true);
});
