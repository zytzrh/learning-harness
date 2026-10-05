import {Window} from 'happy-dom';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import assert from 'node:assert/strict';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'learning-work-test-'));
execFileSync('python3',[path.join(root,'skills/learning-harness/scripts/build_workspace.py'),'--input',path.join(root,'examples/work-lesson.json'),'--output',path.join(temp,'index.html')]);
const html=fs.readFileSync(path.join(temp,'index.html'),'utf8');
fs.rmSync(temp,{recursive:true});
async function load(bridge){
 const w=new Window({url:'https://lesson.example/',settings:{enableJavaScriptEvaluation:true,disableJavaScriptFileLoading:true}});
 const tools=new Map();let requests=[];
 if(bridge){w.document.modelContext={registerTool:async t=>tools.set(t.name,t)};w.document.oai={annotation:{request:(target,options)=>{requests.push({target,options});return {accepted:true};}}};}
 // Write markup without executable scripts, then evaluate owned scripts once.
 w.document.write(html.replace(/<script>([\s\S]*?)<\/script>/g,''));
 for(const match of html.matchAll(/<script>([\s\S]*?)<\/script>/g))w.eval(match[1]);
 await new Promise(r=>setTimeout(r,20));
 const p=w.document.querySelector('[data-block-id]');const range=w.document.createRange();range.setStart(p.firstChild,0);range.setEnd(p.firstChild,4);w.getSelection().addRange(range);p.dispatchEvent(new w.MouseEvent('mouseup',{bubbles:true}));
 w.document.getElementById('question').value='为什么可以排除？';w.document.getElementById('save-question').click();
 assert.equal(w.document.querySelectorAll('.note').length,1);
 return {w,tools,requests};
}
const {w,tools,requests}=await load(true);assert.equal(tools.size,5);
const read=await tools.get('learning_get_state').execute({});const s=read.state,aid=s.annotations[0].id;
[...w.document.querySelectorAll('.note button')].find(b=>b.textContent==='交给当前 Work 回答').click();assert.equal(requests.length,1);assert.equal(requests[0].options.metadata.annotation_id,aid);assert.match(w.document.getElementById('status').textContent,/不代表问题已发送/);
const response=await tools.get('learning_add_answer').execute({expected_revision:s.revision,operation_id:'response-1',annotation_id:aid,text:'因为数组有序。'});assert.equal(response.state.annotations[0].thread.length,1);assert.equal(response.state.annotations[0].status,'open');assert.equal(w.document.querySelector('.message').textContent,'因为数组有序。');
await assert.rejects(tools.get('learning_add_answer').execute({expected_revision:s.revision,operation_id:'response-2',annotation_id:aid,text:'stale'}),/State changed/);
const duplicate=await tools.get('learning_add_answer').execute({expected_revision:s.revision,operation_id:'response-1',annotation_id:aid,text:'因为数组有序。'});assert.equal(duplicate.state.annotations[0].thread.length,1);
assert.equal(JSON.parse(w.localStorage.getItem('learning-harness-v2:'+s.id)).revision,response.state.revision);
const fallback=await load(false);[...fallback.w.document.querySelectorAll('.note button')].find(b=>b.textContent==='交给当前 Work 回答').click();assert.equal(fallback.w.document.getElementById('handoff').open,true);assert.match(fallback.w.document.getElementById('status').textContent,/尚未发送/);
const packet=JSON.parse(fallback.w.document.getElementById('handoff-text').value.split('\n').slice(1).join('\n'));fallback.w.document.getElementById('reply-packet').value=JSON.stringify({...packet,text:'当前对话的手动回答'});fallback.w.document.getElementById('apply-reply').click();assert.equal(fallback.w.document.querySelector('.message').textContent,'当前对话的手动回答');
console.log('DOM contract: annotate → request draft → current-agent write-back, stale/duplicate writes, local persistence, unsupported-host copy/paste: PASS (host APIs mocked)');
await w.happyDOM.close();await fallback.w.happyDOM.close();
