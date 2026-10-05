'use strict';
const $=id=>document.getElementById(id);
const copy=x=>JSON.parse(JSON.stringify(x));
let state=LearningState.validate(JSON.parse($('lesson-state').textContent));
const storageKey='learning-harness-v2:'+state.id;
let selection=null, siteToolsReady=false, storageOK=true;
function notify(message,error=false){$('status').textContent=message;$('status').className=error?'error':'';}
try{const cached=JSON.parse(localStorage.getItem(storageKey)||'null');if(cached){LearningState.validate(cached);if(cached.id===state.id&&cached.revision>=state.revision)state=cached;}localStorage.setItem(storageKey,JSON.stringify(state));}catch(e){storageOK=false;}
function element(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
function button(label,fn){const b=element('button',label);b.type='button';b.onclick=()=>{try{const result=fn();if(result?.catch)result.catch(e=>notify(e.message,true));}catch(e){notify(e.message,true);}};return b;}
function commit(action,input){
  if(storageOK){const cached=JSON.parse(localStorage.getItem(storageKey)||'null');if(cached&&cached.revision>state.revision){state=LearningState.validate(cached);render();throw Error('另一页面更新了学习状态，请重新操作。');}}
  const next=LearningState.change(state,action,input);
  if(storageOK)localStorage.setItem(storageKey,JSON.stringify(next));
  state=next;render();return {state:copy(state),persistence:storageOK?'browser-local':'memory-only'};
}
function capture(){const sel=getSelection();if(!sel||sel.isCollapsed||!sel.rangeCount)return;const r=sel.getRangeAt(0);const parent=n=>(n.nodeType===1?n:n.parentElement)?.closest('[data-block-id]');const p=parent(r.startContainer);if(!p||p!==parent(r.endContainer))return;const prefix=r.cloneRange();prefix.selectNodeContents(p);prefix.setEnd(r.startContainer,r.startOffset);selection={block_id:p.dataset.blockId,start:Array.from(prefix.toString()).length,end:Array.from(prefix.toString()+r.toString()).length,quote:r.toString()};$('quote').textContent=selection.quote;$('selection').hidden=false;notify('选区已保留，请在正文下方填写问题。');}
function handoff(a,target){
  const annotation=document.oai?.annotation;
  if(typeof annotation?.request==='function'){
    try{
      const result=annotation.request(target,{initialComment:('请回答这条学习批注，并把解释写回页面：'+a.question).slice(0,240),metadata:{session_id:state.id,annotation_id:a.id,revision:state.revision,goal:state.goal.slice(0,256)}});
      if(result?.accepted){notify('浏览器已接受批注请求。请在批注编辑器中确认并发送；这还不代表问题已发送。');return;}
    }catch(e){notify('批注编辑器未能打开，已提供手动传递内容。');}
  }
  const block=state.blocks.find(b=>b.id===a.anchor.block_id);
  $('handoff-text').value='请以当前对话的模型回答下面的学习问题，不要另接模型 API。先简短解释；若能访问此页面的 learning_get_state / learning_add_answer 工具，读取最新版本后写回。否则返回可粘贴的 JSON 回答包：{session_id, expected_revision, operation_id, annotation_id, text}。不要自动标记我已掌握。\n'+JSON.stringify({page:location.href,session_id:state.id,expected_revision:state.revision,operation_id:crypto.randomUUID(),goal:state.goal,stack:state.stack.map(id=>state.concepts.find(c=>c.id===id).name),annotation_id:a.id,passage:block.text,question:a.question,quote:a.anchor.quote,thread:a.thread},null,2);
  $('handoff').showModal();notify('尚未发送。复制问题上下文到当前 Work 对话。');
}
function render(){
  document.title=state.goal+' · Learning Harness';$('goal').textContent=state.goal;
  $('path').replaceChildren();state.stack.forEach((cid,i)=>{const c=state.concepts.find(c=>c.id===cid);$('path').append(element('div',c.name,'path-step'+(i===state.stack.length-1?' current':'')));});
  $('back').disabled=state.stack.length===1;
  const current=state.concepts.find(c=>c.id===state.stack.at(-1));$('mastery').textContent={unseen:'未接触',exposed:'已接触 · 尚未验证',self_reported:'自述理解 · 尚未验证'}[current.status];
  $('document').replaceChildren();
  state.blocks.forEach(block=>{
    const section=element('section',undefined,'block'),p=element('p',undefined,'passage');p.dataset.blockId=block.id;
    const annotations=state.annotations.filter(a=>a.anchor.block_id===block.id),chars=Array.from(block.text),cuts=[...new Set([0,chars.length,...annotations.flatMap(a=>[a.anchor.start,a.anchor.end])])].sort((a,b)=>a-b);
    for(let i=0;i<cuts.length-1;i++){const lo=cuts[i],hi=cuts[i+1],str=chars.slice(lo,hi).join('');p.append(annotations.some(a=>a.status==='open'&&a.anchor.start<hi&&a.anchor.end>lo)?element('mark',str):document.createTextNode(str));}section.append(p);
    annotations.forEach(a=>section.append(button((a.status==='open'?'? ':'✓ ')+a.question.slice(0,28),()=>{$('note-'+a.id).scrollIntoView({behavior:'smooth',block:'center'});})));$('document').append(section);
  });
  $('annotations').replaceChildren();
  if(!state.annotations.length)$('annotations').append(element('p','你的问题会留在它发生的位置。','muted'));
  state.annotations.forEach(a=>{
    const note=element('article',undefined,'note');note.id='note-'+a.id;note.setAttribute('oai-annotatable','学习问题：'+a.question.slice(0,80));note.setAttribute('oai-annotation-metadata',JSON.stringify({session_id:state.id,annotation_id:a.id,revision:state.revision}));
    note.append(element('small',a.status==='open'?'待理解':'已解决'),element('blockquote',a.anchor.quote),element('p',a.question,'question'));
    a.thread.forEach(m=>note.append(element('div',m.role==='user'?'你的追问':'当前对话的解释','role'),element('p',m.text,'message')));
    note.append(button('交给当前 Work 回答',()=>handoff(a,note)),button(a.status==='open'?'我已理解，解决':'重新打开',()=>commit('resolve',{annotation_id:a.id,resolved:a.status==='open'})));
    const input=element('textarea');input.setAttribute('aria-label','追问：'+a.question);input.placeholder='继续追问…';note.append(input,button('保存追问',()=>{commit('followup',{annotation_id:a.id,text:input.value});notify('追问已保存。点击「交给当前 Work 回答」继续。');}));$('annotations').append(note);
  });
}
function capabilities(){const annotations=typeof document.oai?.annotation?.request==='function';$('capabilities').textContent=(annotations?'支持浏览器批注':'此环境需手动复制问题')+' · '+(siteToolsReady?'Work 可通过网页工具读写':'网页工具尚不可用')+' · '+(storageOK?'学习状态保存在此浏览器，请定期导出':'浏览器存储不可用，仅当前页面有效，请导出');}
$('document').addEventListener('mouseup',capture);$('document').addEventListener('keyup',capture);$('document').addEventListener('touchend',()=>setTimeout(capture,20));
$('save-question').onclick=()=>{try{if(!selection)throw Error('请先划选一句话');commit('annotate',{...selection,question:$('question').value});selection=null;$('selection').hidden=true;$('question').value='';notify('批注已保存。在右侧点击「交给当前 Work 回答」。');}catch(e){notify(e.message,true);}};
$('cancel').onclick=()=>{$('selection').hidden=true;selection=null;};
$('back').onclick=()=>{try{commit('back',{});}catch(e){notify(e.message,true);}};
$('push').onclick=()=>{try{commit('push',{name:$('prerequisite').value});$('prerequisite').value='';}catch(e){notify(e.message,true);}};
$('understood').onclick=()=>{try{commit('understanding',{text:$('evidence').value});$('evidence').value='';notify('已保存你的复述，没有自动判定已验证。');}catch(e){notify(e.message,true);}};
$('copy').onclick=async()=>{try{await navigator.clipboard.writeText($('handoff-text').value);notify('已复制，请粘贴到当前对话。尚未发送。');}catch(e){$('handoff-text').select();notify('请手动复制已选中的文本。');}};
$('close-handoff').onclick=()=>$('handoff').close();
$('apply-reply').onclick=()=>{try{const p=JSON.parse($('reply-packet').value);if(p.session_id!==state.id)throw Error('回答包属于另一个学习会话');if(!Number.isInteger(p.expected_revision)||!p.operation_id)throw Error('回答包缺少版本或操作 ID');commit('answer',p);$('reply-packet').value='';notify('解释已写入批注。');}catch(e){notify(e.message,true);}};
$('export').onclick=()=>{const link=element('a');const url=URL.createObjectURL(new Blob([JSON.stringify(state,null,2)],{type:'application/json'}));link.href=url;link.download='learning-state-'+state.id+'.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
window.addEventListener('storage',e=>{if(e.key!==storageKey||!e.newValue)return;try{const next=LearningState.validate(JSON.parse(e.newValue));if(next.revision>state.revision){state=next;render();notify('已同步另一页面的更新。');}}catch(e){notify('忽略了无效的浏览器状态。',true);}});
async function registerTools(){
  const mc=document.modelContext;
  if(typeof mc?.registerTool!=='function')return;
  const schema=props=>({type:'object',properties:props,required:Object.keys(props),additionalProperties:false});
  const string={type:'string'},revision={type:'integer',minimum:0};
  const writeProps={expected_revision:revision,operation_id:string};
  const write=(action,props)=>({inputSchema:schema({...writeProps,...props}),execute:async input=>{
    if(!Number.isInteger(input.expected_revision)||typeof input.operation_id!=='string'||!input.operation_id.trim())throw Error('Read state first; include current revision and a unique operation_id');
    return commit(action,input);
  }});
  const tools=[
    {name:'learning_get_state',description:'Read this lesson, anchored questions, answer threads, learner evidence and current revision. Does not call a model.',inputSchema:schema({}),annotations:{readOnlyHint:true},execute:async()=>({state:copy(state),persistence:storageOK?'browser-local':'memory-only'})},
    {name:'learning_add_answer',description:'Write an explanation composed by the CURRENT conversation agent to one existing annotation. Does not invoke an external model or resolve the question. Returns state for durable checkpointing.',...write('answer',{annotation_id:string,text:string})},
    {name:'learning_append_content',description:'Append 1–8 short teaching paragraphs composed by the current agent. Preserve all existing source blocks and anchors.',...write('append',{paragraphs:{type:'array',items:string,minItems:1,maxItems:8}})},
    {name:'learning_enter_prerequisite',description:'Enter a prerequisite branch while preserving the return path. Use when the learner asks or agrees to take this branch.',...write('push',{name:string})},
    {name:'learning_return',description:'Return to the parent concept, without asserting mastery.',...write('back',{})}
  ];
  for(const tool of tools)await mc.registerTool(tool);
  siteToolsReady=true;capabilities();
}
render();capabilities();registerTools().catch(e=>notify('网页工具注册失败；可以使用手动传递方式。',true));
