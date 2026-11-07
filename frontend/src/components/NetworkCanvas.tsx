import { memo,useEffect, useRef } from 'react';
import cytoscape, { type Core } from 'cytoscape';
import { Maximize, Minus, Plus } from 'lucide-react';
import type { GraphView, Score, GraphEdge, RiskOverlay } from '../api/types';
export const NetworkCanvas=memo(function NetworkCanvas({graph, scores, top, onNode, onEdge,risk}: {graph:GraphView; scores:Score[]; top:number; onNode:(id:string)=>void; onEdge:(edge:GraphEdge)=>void;risk?:RiskOverlay|null}) {
  const container = useRef<HTMLDivElement>(null); const core = useRef<Core | null>(null);
  useEffect(() => {
    if (!container.current) return;
    const started=performance.now();
    const cy = cytoscape({container:container.current, elements:[...graph.nodes.map(n => ({data:{...n, label:n.id.startsWith('SYN-BANK-')?n.id.replace('SYN-BANK-','Bank '):n.label,strength:n.in_strength+n.out_strength}})), ...graph.edges.map(e => ({data:e}))],
      style:[{selector:'node',style:{label:'data(label)',width:28,height:28,'background-color':'#408b88',color:'#64748b','font-size':11,'text-wrap':'wrap','text-valign':'bottom','text-margin-y':7,'border-width':2,'border-color':'#fff'}},
        {selector:'edge',style:{width:1,'line-color':'#94b9b5','target-arrow-color':'#94b9b5','target-arrow-shape':'triangle','curve-style':'bezier',opacity:.24,'arrow-scale':.6}},
        {selector:':selected',style:{'border-color':'#172c42','border-width':4,'background-color':'#d9ae53'}},
        {selector:'.top',style:{'background-color':'#dbb25d','border-color':'#fff'}},
        {selector:'.muted',style:{'background-opacity':.55}}], layout:{name:'concentric',concentric:n=>Math.log1p(Number(n.data('strength'))),levelWidth:()=>2,padding:45,animate:false}, minZoom:.15,maxZoom:5});
    const theme=()=>{ if(container.current)cy.nodes().style('color',getComputedStyle(container.current).getPropertyValue('--text').trim()); };
    theme(); const themeObserver=new MutationObserver(theme);const app=container.current.closest('.app');if(app)themeObserver.observe(app,{attributes:true,attributeFilter:['class']});
    cy.nodes().forEach(n => { const size=18+Math.min(30,Math.log1p(Number(n.data('strength')))*2); n.style({width:size,height:size}); });
    const readableLabels=()=>cy.nodes().style('font-size',10/cy.zoom());
    cy.on('zoom',readableLabels);readableLabels();
    cy.on('tap','node',e=>onNode(e.target.id())); cy.on('tap','edge',e=>onEdge(e.target.data() as GraphEdge));
    core.current=cy; const resize=new ResizeObserver(()=>{cy.resize();cy.fit(undefined,65);}); resize.observe(container.current);
    performance.measure('fnb.network.initialize',{start:started,end:performance.now()});
    return ()=>{resize.disconnect();themeObserver.disconnect();cy.destroy();core.current=null;};
  },[graph,onNode,onEdge]);
  useEffect(()=>{const cy=core.current;if(!cy)return; const ids=new Set(scores.slice(0,top).map(s=>s.node_id));cy.nodes().removeClass('top muted');if(ids.size)cy.nodes().forEach(n=>{n.addClass(ids.has(n.id())?'top':'muted');});},[scores,top,graph]);
  useEffect(()=>{
    const cy=core.current;if(!cy)return;
    cy.nodes().removeStyle('label background-color border-color border-width');cy.edges().removeStyle('line-color source-arrow-color target-arrow-color source-arrow-shape target-arrow-shape opacity width');
    if(!risk){const ids=new Set(scores.slice(0,top).map(s=>s.node_id));cy.nodes().removeClass('top muted');if(ids.size)cy.nodes().forEach(n=>{n.addClass(ids.has(n.id())?'top':'muted');});return;}
    const frame=risk.scenario.history[risk.step];if(!frame)return;
    cy.nodes().removeClass('top muted');
    cy.nodes().forEach(n=>{const h=frame.distress[n.id()]??0;const shocked=(risk.scenario.initial_shocks[n.id()]??0)>0;n.style({label:`${String(n.data('label'))}\nh=${h.toFixed(3)}`,'background-color':h>0?'#d9ac5b':'#408b88','border-color':shocked?'#cb5c52':'#fff','border-width':shocked?5:2});});
    for(const t of frame.transmissions){const edge=cy.getElementById(`${t.exposure_source}:${t.exposure_target}`);edge.style({'line-color':'#cb5c52','source-arrow-color':'#cb5c52','source-arrow-shape':'triangle','target-arrow-shape':'none',opacity:.95,width:3});}
  },[risk,graph,scores,top]);
  return <div className="network-wrap"><div ref={container} className="network-canvas" data-testid="network-graph" role="img" aria-label={`Directed exposure network: ${graph.visible_nodes} visible nodes and ${graph.visible_edges} visible edges. Search and node list provide keyboard access.`}/><div className="canvas-label"><span className="live-dot"/> DIRECTED EXPOSURE NETWORK</div><div className="canvas-controls"><button aria-label="Zoom in" onClick={()=>core.current?.zoom((core.current?.zoom()??1)*1.3)}><Plus size={17}/></button><button aria-label="Zoom out" onClick={()=>core.current?.zoom((core.current?.zoom()??1)/1.3)}><Minus size={17}/></button><button aria-label="Fit graph" onClick={()=>core.current?.fit(undefined,65)}><Maximize size={17}/></button></div><div className="canvas-legend">{risk ? <>Risk step {risk.step} · red ring: shocked · amber: distress <span>Red arrows: debtor → creditor loss</span></> : <><i/> Exposure network <i className="gold"/> Top {top} scores <span>→ Creditor to debtor</span></>}</div></div>;
});
