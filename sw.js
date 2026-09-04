const CACHE='treino-v4';
const ASSETS=['./','index.html','manifest.webmanifest',
  'icon-180.png','icon-192.png','icon-512.png','icon-maskable-512.png'];

/* Cada arquivo é cacheado por conta própria. Com addAll(), um único 404 fazia a
   instalação inteira falhar e o app ficava sem service worker — sem offline. */
self.addEventListener('install',e=>{
  e.waitUntil((async()=>{
    const c=await caches.open(CACHE);
    await Promise.all(ASSETS.map(a=>c.add(a).catch(()=>{})));
    await self.skipWaiting();
  })());
});

self.addEventListener('activate',e=>{
  e.waitUntil((async()=>{
    const keys=await caches.keys();
    await Promise.all(keys.filter(n=>n!==CACHE).map(n=>caches.delete(n)));
    await self.clients.claim();
  })());
});

const isDoc=req=>{
  if(req.mode==='navigate') return true;
  const p=new URL(req.url).pathname;
  return p.endsWith('/')||p.endsWith('index.html');
};

self.addEventListener('fetch',e=>{
  if(e.request.method!=='GET') return;
  if(new URL(e.request.url).origin!==location.origin) return;

  if(isDoc(e.request)){
    /* rede primeiro: uma versão nova do treino chega na próxima abertura com sinal */
    e.respondWith((async()=>{
      try{
        const res=await fetch(e.request,{cache:'reload'});
        const c=await caches.open(CACHE); c.put('index.html',res.clone());
        return res;
      }catch(err){
        return (await caches.match('index.html'))||Response.error();
      }
    })());
    return;
  }

  e.respondWith((async()=>{
    const hit=await caches.match(e.request);
    if(hit) return hit;
    try{
      const res=await fetch(e.request);
      const c=await caches.open(CACHE); c.put(e.request,res.clone());
      return res;
    }catch(err){ return Response.error(); }
  })());
});
