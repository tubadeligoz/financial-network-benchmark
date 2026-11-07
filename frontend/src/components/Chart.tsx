import { useEffect, useRef } from 'react';
import * as echarts from 'echarts/core';
import { BarChart, LineChart, HeatmapChart } from 'echarts/charts';
import { GridComponent, TooltipComponent, LegendComponent, VisualMapComponent } from 'echarts/components';
import { SVGRenderer } from 'echarts/renderers';
import type { EChartsCoreOption } from 'echarts/core';
import { Download } from 'lucide-react';
echarts.use([BarChart,LineChart,HeatmapChart,GridComponent,TooltipComponent,LegendComponent,VisualMapComponent,SVGRenderer]);
export function Chart({title,option}:{title:string;option:EChartsCoreOption}) {
  const ref=useRef<HTMLDivElement>(null);const instance=useRef<echarts.EChartsType|null>(null);
  useEffect(()=>{
    if(!ref.current)return;
    const chart=echarts.init(ref.current,undefined,{renderer:'svg'});instance.current=chart;
    const observer=new ResizeObserver(()=>chart.resize());observer.observe(ref.current);
    const theme=new MutationObserver(()=>{
      if(!ref.current)return;
      const color=getComputedStyle(ref.current).getPropertyValue('--muted').trim();
      chart.setOption({textStyle:{color},xAxis:{axisLabel:{color},nameTextStyle:{color}},yAxis:{axisLabel:{color},nameTextStyle:{color}},legend:{textStyle:{color}}});
    });
    const app=ref.current.closest('.app');if(app)theme.observe(app,{attributes:true,attributeFilter:['class']});
    return()=>{observer.disconnect();theme.disconnect();chart.dispose();instance.current=null;};
  },[]);
  useEffect(()=>{
    if(!ref.current||!instance.current)return;
    const color=getComputedStyle(ref.current).getPropertyValue('--muted').trim();
    instance.current.setOption({...option,textStyle:{fontFamily:'Segoe UI, sans-serif',color},backgroundColor:'transparent'},{notMerge:true});
    instance.current.setOption({xAxis:{axisLabel:{color},nameTextStyle:{color}},yAxis:{axisLabel:{color},nameTextStyle:{color}},legend:{textStyle:{color}}});
  },[option]);
  const download=()=>{const url=instance.current?.getDataURL({type:'svg'});if(!url)return;const a=document.createElement('a');a.href=url;a.download=`${title.toLowerCase().replace(/[^a-z0-9]+/g,'-')}.svg`;a.click();};
  return <section className="panel padded chart-panel"><div className="section-title"><h2>{title}</h2><button className="icon-button" aria-label={`Export ${title} as SVG`} onClick={download}><Download size={17}/></button></div><div className="chart" ref={ref} role="img" aria-label={`${title}. Numerical values are available in the adjacent table.`}/></section>;
}
