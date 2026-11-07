import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,render} from '@testing-library/react';
import * as echarts from 'echarts/core';
import {Chart} from '../src/components/Chart';
vi.mock('echarts/core',()=>({use:vi.fn(),init:vi.fn()}));
afterEach(()=>{cleanup();vi.unstubAllGlobals();vi.restoreAllMocks();});
it('updates chart data without disposing/reinitializing the chart instance',()=>{
  const chart={setOption:vi.fn(),resize:vi.fn(),dispose:vi.fn()};
  vi.mocked(echarts.init).mockReturnValue(chart as unknown as ReturnType<typeof echarts.init>);
  vi.stubGlobal('ResizeObserver',class {observe(){} disconnect(){}});
  const view=render(<Chart title="SYNTHETIC TEST chart" option={{series:[{type:'bar',data:[1]}]}}/>);
  view.rerender(<Chart title="SYNTHETIC TEST chart" option={{series:[{type:'bar',data:[2]}]}}/>);
  expect(echarts.init).toHaveBeenCalledTimes(1);expect(chart.dispose).not.toHaveBeenCalled();
  view.unmount();expect(chart.dispose).toHaveBeenCalledTimes(1);
});
