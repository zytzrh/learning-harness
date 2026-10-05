/* Model-independent state transitions. No inference, network calls, or host APIs. */
(function(root) {
'use strict';
const clone = x => JSON.parse(JSON.stringify(x));
const id = () => globalThis.crypto.randomUUID();
const text = (x, max=12000) => {
  if(typeof x !== 'string' || !x.trim() || x.length > max) throw Error('Invalid or oversized text');
  return x.trim();
};
function validate(s) {
  if(!s || s.schema_version!==2 || typeof s.id!=='string' || !Number.isInteger(s.revision) || s.revision<0) throw Error('Unsupported learning state');
  text(s.goal,500);
  for(const key of ['blocks','annotations','concepts','stack','events','operations']) if(!Array.isArray(s[key])) throw Error('Invalid '+key);
  if(!s.stack.length || !s.blocks.length) throw Error('Empty learning state');
  const unique=xs=>new Set(xs.map(x=>x.id)).size===xs.length;
  if(!unique(s.blocks)||!unique(s.annotations)||!unique(s.concepts)) throw Error('Duplicate IDs');
  for(const b of s.blocks){text(b.id,100);text(b.text,30000);}
  for(const c of s.concepts){text(c.id,100);text(c.name,500);if(!['unseen','exposed','self_reported'].includes(c.status)||!Array.isArray(c.evidence))throw Error('Invalid concept');}
  if(s.stack.some(cid=>!s.concepts.some(c=>c.id===cid)))throw Error('Unknown concept in stack');
  for(const a of s.annotations){
    text(a.id,100);text(a.question,4000);
    const b=s.blocks.find(b=>b.id===a.anchor?.block_id), chars=b&&Array.from(b.text);
    if(!chars||!Number.isInteger(a.anchor.start)||!Number.isInteger(a.anchor.end)||a.anchor.start<0||a.anchor.end>chars.length||a.anchor.start>=a.anchor.end||chars.slice(a.anchor.start,a.anchor.end).join('')!==a.anchor.quote)throw Error('Invalid anchor');
    if(!['open','resolved'].includes(a.status)||!Array.isArray(a.thread)||!s.concepts.some(c=>c.id===a.concept_id))throw Error('Invalid annotation');
    for(const m of a.thread){if(!['user','assistant'].includes(m.role))throw Error('Invalid message');text(m.text,30000);}
  }
  return s;
}
function change(original, action, input) {
  validate(original);
  const p=clone(input||{}), s=clone(original);
  if(p.operation_id && s.operations.includes(p.operation_id)) return s;
  if(p.expected_revision!==undefined && p.expected_revision!==s.revision) throw Error('State changed; read learning_get_state and retry with the current revision');
  const a=s.annotations.find(a=>a.id===p.annotation_id);
  const current=()=>s.concepts.find(c=>c.id===s.stack.at(-1));
  if(action==='annotate') {
    const b=s.blocks.find(b=>b.id===p.block_id), chars=b&&Array.from(b.text);
    if(!chars||!Number.isInteger(p.start)||!Number.isInteger(p.end)||p.start<0||p.end>chars.length||p.end<=p.start||chars.slice(p.start,p.end).join('')!==p.quote)throw Error('Selection no longer matches the passage');
    s.annotations.push({id:id(),anchor:{block_id:b.id,start:p.start,end:p.end,quote:p.quote},question:text(p.question,4000),concept_id:current().id,status:'open',thread:[]});
  } else if(action==='followup') {
    if(!a)throw Error('Unknown annotation');
    a.thread.push({role:'user',text:text(p.text,4000)});a.status='open';
  } else if(action==='answer') {
    if(!a)throw Error('Unknown annotation');
    a.thread.push({role:'assistant',text:text(p.text,30000),source:'current-agent'});
    const c=s.concepts.find(c=>c.id===a.concept_id);if(c.status==='unseen')c.status='exposed';
  } else if(action==='resolve') {
    if(!a||typeof p.resolved!=='boolean')throw Error('Invalid resolution');
    a.status=p.resolved?'resolved':'open';
  } else if(action==='append') {
    if(!Array.isArray(p.paragraphs)||!p.paragraphs.length||p.paragraphs.length>8)throw Error('Provide 1–8 short paragraphs');
    p.paragraphs.forEach(t=>s.blocks.push({id:id(),text:text(t),concept_id:current().id}));
  } else if(action==='push') {
    const name=text(p.name,200), existing=s.concepts.find(c=>c.name===name);
    if(existing&&s.stack.includes(existing.id))throw Error('Concept already on active path');
    const c=existing||{id:id(),name,status:'unseen',evidence:[]};
    if(!existing)s.concepts.push(c);s.stack.push(c.id);
  } else if(action==='back') {
    if(s.stack.length<2)throw Error('Already at the goal');s.stack.pop();
  } else if(action==='understanding') {
    current().evidence.push({kind:'learner_explanation',text:text(p.text,8000),verified:false});current().status='self_reported';
  } else throw Error('Unknown action');
  s.revision++;
  s.events.push({type:action,revision:s.revision,at:new Date().toISOString()});
  if(p.operation_id)s.operations.push(text(p.operation_id,100));
  return validate(s);
}
const api={validate,change};
if(typeof module!=='undefined'&&module.exports)module.exports=api;
else root.LearningState=api;
})(globalThis);
