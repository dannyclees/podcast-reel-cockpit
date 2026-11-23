// Fake Buffer, fake database. Run from app/: node tests/post_test.mjs
import './_stubs.mjs';
process.env.SUPABASE_URL='http://fake'; process.env.SUPABASE_SERVICE_KEY='k'; process.env.POSTING_ENABLED='1'; process.env.BUFFER_API_KEY='k';
process.env.BUFFER_CHANNELS=JSON.stringify({youtube:{id:'cy',name:'y'},instagram:{id:'ci',name:'i'},tiktok:{id:'ct',name:'t'}});
const J=(o,c=200)=>new Response(JSON.stringify(o),{status:c});
let extra={}, row, creates, deletes, bufPosts, opts, seq;
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
function reset(extraRow={},ex={}){ row={id:'e/x',episode_id:'e',status:'approved',round:1,track:'none',sfx:false,posted:{},updated_at:"2026-01-01T00:00:00.000+00:00",...extraRow}; creates=[];deletes=[];extra=ex;bufPosts=[];opts={};seq=0; }
globalThis.fetch=async(url,init={})=>{ url=String(url); const b=init.body?JSON.parse(init.body):null;
  if(url.startsWith('https://api.buffer.com')){ await sleep(5); const q=b.query;
    if(q.includes('organizations')) return J({data:{account:{organizations:[{id:'o'}]}}});
    if(q.includes('posts(input')){ if(opts.listFails) return J({errors:[{message:'boom'}]}); const c=b.variables.i.filter.channelIds; const all=opts.empty?[]:bufPosts.concat(['cy','ci','ct'].map(ch=>({id:'seed'+ch,status:'sent',text:'seed '+ch,channelId:ch}))).filter(p=>c.includes(p.channelId)); const off=+(b.variables.after||0); const page=all.slice(off,off+(opts.pageSize||100)); return J({data:{posts:{edges:page.map(node=>({node})),pageInfo:{hasNextPage:off+page.length<all.length,endCursor:String(off+page.length)}}}}); }
    if(q.includes('createPost')){ const i=b.variables.i; const p={id:'b'+(++seq),status:'scheduled',dueAt:i.dueAt,text:i.text,channelId:i.channelId}; creates.push(p); bufPosts.push(p); return J({data:{createPost:{__typename:'PostActionSuccess',post:p}}}); }
    if(q.includes('deletePost')){ deletes.push(b.variables.i.id); if(opts.deleteFails) return J({data:{deletePost:{__typename:'NotFoundError'}}}); bufPosts=bufPosts.filter(p=>p.id!==b.variables.i.id); return J({data:{deletePost:{__typename:'DeletePostSuccess'}}}); }
    throw new Error('buffer? '+q); }
  if(url.includes('/storage/v1/object/sign')){ await sleep(20); if(opts.signFails) return J({},500); return J(b.paths.map(path=>({path,signedURL:'/s/'+path}))); }
  if(url.includes('/rest/v1/shorts_items')){ const u=new URL(url); const m=init.method||'GET';
    const idf=u.searchParams.get('id')||''; const all=()=>[row,...Object.values(extra)];
    if(m==='GET'){ if(idf.startsWith('neq.')) return J(structuredClone(all().filter(r=>r.id!==idf.slice(4)))); if(idf.startsWith('eq.')) return J(structuredClone(all().filter(r=>r.id===idf.slice(3)))); return J(structuredClone(all())); }
    await sleep(1); const id=idf.slice(3); const cur=id===row.id?row:extra[id]; const ue=u.searchParams.get('updated_at'); if(ue&&ue!=='eq.'+cur.updated_at) return J([]);
    const nx={...cur,...b}; if(id===row.id) row=nx; else extra[id]=nx; return J([structuredClone(nx)]); }
  if(url.includes('/rest/v1/shorts_versions')) return J([{master_path:'m/master.mp4',tracks:{}}]);
  if(url.includes('/rest/v1/shorts_feedback')) return J([{ok:1}]);
  throw new Error('fetch? '+url); };
const {default:handler}=await import(new URL('../api/post.js',import.meta.url).href);
const call=b=>new Promise(ok=>{const res={setHeader(){},end(s){ok({code:res.statusCode,body:JSON.parse(s)})}};handler({method:'POST',body:b},res);});
const iso=new Date(Date.now()+864e5).toISOString(), P=['youtube','instagram','tiktok'];
const req=(x={})=>({op:'schedule',id:'e/x',platforms:P,due:Object.fromEntries(P.map(k=>[k,{iso}])),copy:Object.fromEntries(P.map(k=>[k,{text:'Hook line '+k,title:'T'}])),...x});
let bad=0; const ok=(n,c,info='')=>{console.log((c?'PASS ':'FAIL ')+n,info); if(!c)bad++;};
reset(); let [a,b]=await Promise.all([call(req()),call(req())]);
ok('two at the same time: 3 posts, not 6',creates.length===3,`creates=${creates.length} codes=${a.code},${b.code}`);
ok('two at the same time: one refused',[a.code,b.code].sort().join()==='200,409');
ok('all three scheduled',P.every(p=>row.posted[p].state==='scheduled'));
reset(); await call(req()); let n=creates.length; await sleep(2); let c2=await call(req());
ok('second click later: nothing new',creates.length===n,`creates=${creates.length} code=${c2.code}`);
reset(); const rs=await Promise.all([...Array(10)].map(()=>call(req())));
ok('ten at once: still 3',creates.length===3,`creates=${creates.length}`);
reset(); bufPosts=[{id:'orph',status:'scheduled',dueAt:iso,text:'Hook  line instagram',channelId:'ci'}]; await call(req());
ok('already in Buffer: adopted, not booked',creates.length===2&&row.posted.instagram.buffer_id==='orph',`creates=${creates.length}`);
reset(); bufPosts=[{id:'old',status:'sent',sentAt:'2026-01-01',externalLink:'https://x',text:'Hook line tiktok',channelId:'ct'}]; await call(req());
ok('already live: marked posted, not booked',row.posted.tiktok.state==='posted'&&creates.length===2);
reset(); opts.listFails=true; await call(req());
ok('Buffer check fails: books nothing',creates.length===0&&row.posted.youtube.state==='failed',row.posted.youtube.error);
reset({status:'scheduled',posted:{youtube:{state:'scheduled',buffer_id:'w1'}}}); bufPosts=[{id:'w1',status:'scheduled',dueAt:iso,text:'Hook line youtube',channelId:'cy'}]; opts.deleteFails=true; await call(req({now:true,platforms:['youtube']}));
ok('post now, old post will not delete: no second post',creates.length===0&&row.posted.youtube.state==='failed',row.posted.youtube.error);
reset({status:'scheduled',posted:{youtube:{state:'scheduled',buffer_id:'w1'}}}); bufPosts=[{id:'w1',status:'scheduled',dueAt:iso,text:'Hook line youtube',channelId:'cy'}]; await call(req({now:true,platforms:['youtube']}));
ok('post now, old post deleted: exactly one new',creates.length===1&&deletes[0]==='w1');
reset(); opts.signFails=true; let f=await call(req());
ok('prepare fails: claim given back',f.code>=500&&!row.posted.youtube&&creates.length===0,`code=${f.code}`);
reset(); await call(req()); for(const p of P) await call({op:'cancel',id:'e/x',platform:p}); await call(req());
ok('cancel then book again: works',creates.length===6&&P.every(p=>row.posted[p].state==='scheduled'),`creates=${creates.length}`);
reset({posted:{youtube:{state:'booking',at:new Date(Date.now()-3600e3).toISOString()}}}); await call(req({platforms:['youtube']}));
ok('old crashed claim can be retried',creates.length===1);
reset(); opts.pageSize=2; bufPosts=[...Array(7)].map((_,i)=>({id:'o'+i,status:'sent',sentAt:'2026',text:'other '+i,channelId:'cy'})).concat([{id:'deep',status:'sent',sentAt:'2026',externalLink:'https://x',text:'Hook line youtube',channelId:'cy'}]); await call(req({platforms:['youtube']}));
ok('match on a later page: still found',creates.length===0&&row.posted.youtube.buffer_id==='deep');
reset(); opts.empty=true; await call(req());
ok('Buffer returns nothing: books nothing',creates.length===0&&row.posted.youtube.state==='failed',row.posted.youtube.error);
const other=(id,posted={})=>({id,episode_id:'e',status:'approved',round:1,track:'none',sfx:false,posted,updated_at:'2026-01-01T00:00:00.000+00:00'});
const dueOf=r=>P.map(p=>r.posted[p]?.due); const reqB=(id,x={})=>req({id,copy:Object.fromEntries(P.map(k=>[k,{text:id+' copy '+k,title:'T'}])),...x});
reset(); extra={'e/y':other('e/y')}; await Promise.all([call(req()),call(reqB('e/y'))]);
let d1=+new Date(row.posted.youtube.due),d2=+new Date(extra['e/y'].posted.youtube.due);
ok('two Shorts clicked at once: 4 h apart',Math.abs(d1-d2)===4*3600e3&&creates.length===6,`gap=${Math.abs(d1-d2)/3600e3}h creates=${creates.length}`);
ok('all three platforms of a Short share one time',new Set(dueOf(row)).size===1&&new Set(dueOf(extra['e/y'])).size===1);
reset(); extra={'e/y':other('e/y'),'e/z':other('e/z')}; await Promise.all([call(req()),call(reqB('e/y')),call(reqB('e/z'))]);
const ts=[row,extra['e/y'],extra['e/z']].map(r=>+new Date(r.posted.youtube.due)).sort((a,b)=>a-b);
ok('three at once: three times',ts[1]-ts[0]===4*3600e3&&ts[2]-ts[1]===4*3600e3,ts.map(t=>(t-ts[0])/3600e3).join());
reset(); extra={'e/y':other('e/y',{youtube:{state:'scheduled',due:iso,buffer_id:'q'}})}; await call(req());
ok('time already taken: moves 4 h on',+new Date(row.posted.tiktok.due)===+new Date(iso)+4*3600e3,row.posted.tiktok.due);
const later=new Date(+new Date(iso)+5*3600e3).toISOString(); reset(); extra={'e/y':other('e/y',{youtube:{state:'scheduled',due:iso,buffer_id:'q'}})}; await call(req({due:Object.fromEntries(P.map(k=>[k,{iso:later}]))}));
ok('free time: stays where asked',row.posted.youtube.due===later);
reset(); extra={'e/y':other('e/y',{youtube:{state:'scheduled',due:new Date(Date.now()+60000).toISOString(),buffer_id:'q'}})}; await call(req({now:true}));
ok('post now: not moved',creates.length===3&&!creates.some(c=>c.dueAt));
extra={}; reset(); await call(req());
ok('no other Shorts: stays where asked',row.posted.youtube.due===iso);
console.log(bad?`${bad} FAILED`:'ALL PASS'); process.exit(bad?1:0);
