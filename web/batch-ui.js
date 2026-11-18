import {CaptureZip,clueCapturePlan,safeCaptureName} from './batch-capture.js';

const $=id=>document.getElementById(id);
const esc=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

export function setupBatchCapture(adapter){
  let running=false,cancelled=false,downloadUrl=null,downloadBlob=null,saving=false;
  const readyMaps=()=>adapter.maps().filter(map=>map.ready&&!map.library&&map.nodes>0);
  function chosenMaps(){
    const scope=$('batch-scope').value;
    const selected=new Set([...$('batch-map-options').querySelectorAll('input:checked')].map(input=>input.value));
    return readyMaps().filter(map=>scope==='all'||(scope==='current'?map.id===adapter.currentMap():selected.has(map.id)));
  }
  function summary(){
    const maps=chosenMaps();$('batch-summary').textContent=`${maps.length} ${maps.length===1?'map':'maps'} · ${maps.length*6} screenshots`;
    $('batch-map-options').classList.toggle('hidden',$('batch-scope').value!=='selected');
    $('start-batch').disabled=running||saving||!maps.length||!adapter.currentMap();
  }
  $('open-batch-capture').onclick=()=>{
    $('batch-map-options').innerHTML=readyMaps().map(map=>`<label><input type="checkbox" value="${esc(map.id)}" checked> ${esc(map.name)}</label>`).join('');
    if(!$('batch-seed').value)$('batch-seed').value=crypto.randomUUID();
    summary();$('batch-dialog').showModal();
  };
  $('batch-scope').onchange=summary;$('batch-map-options').onchange=summary;
  $('batch-new-seed').onclick=()=>$('batch-seed').value=crypto.randomUUID();
  $('close-batch').onclick=()=>{if(!running)$('batch-dialog').close();};
  $('batch-dialog').addEventListener('cancel',event=>{if(running){event.preventDefault();cancel();}});
  function cancel(){if(!running||cancelled)return;cancelled=true;adapter.cancelLoad();$('cancel-batch').disabled=true;$('batch-status').textContent='Cancelling; completed maps will be kept. Restoring your view…';}
  $('cancel-batch').onclick=cancel;
  $('batch-save-local').onclick=async()=>{
    if(!downloadBlob||running||saving)return;
    saving=true;summary();const button=$('batch-save-local');button.disabled=true;$('batch-local-path').textContent='Saving ZIP on this computer…';
    try{
      const response=await fetch('/api/captures',{method:'POST',headers:{'Content-Type':'application/zip'},body:downloadBlob});
      const result=await response.json();if(!response.ok)throw new Error(result.error||'Local save failed.');
      $('batch-local-path').textContent='Saved: '+result.path;
    }catch(error){$('batch-local-path').textContent=error.message;}
    finally{saving=false;button.disabled=false;summary();}
  };
  $('start-batch').onclick=async()=>{
    if(running||saving)return;
    const maps=chosenMaps(),seed=$('batch-seed').value.trim();
    if(!maps.length)return;
    if(!seed){$('batch-status').textContent='Enter a seed or choose New seed.';return;}
    const [width,height]=$('batch-size').value.split('x').map(Number);
    const settings={width,height,seed,fixedCamera:$('batch-camera').value==='per-map',cumulative:$('batch-reveal').value==='cumulative',distribution:$('batch-distribution').value,
      layers:{geometry:$('batch-geometry').checked,portals:true,labels:false,lines:false,allAngles:false,cutaway:$('batch-cutaway').checked}};
    const saved=adapter.snapshot(),zip=new CaptureZip();
    const manifest={format:'portal-atlas-clue-batch',version:1,created:new Date().toISOString(),settings,maps:[],errors:[],cancelled:false};
    running=true;cancelled=false;adapter.setRunning(true);
    $('batch-settings').disabled=true;$('close-batch').disabled=true;$('start-batch').disabled=true;$('cancel-batch').disabled=false;
    $('batch-progress').value=0;$('batch-progress').max=maps.length*6;$('batch-report').textContent='';
    $('batch-download').classList.add('hidden');
    $('batch-save-local').classList.add('hidden');$('batch-local-path').textContent='';downloadBlob=null;
    if(downloadUrl){URL.revokeObjectURL(downloadUrl);downloadUrl=null;}
    let completed=0;
    try{
      for(const map of maps){
        if(cancelled)break;
        $('batch-status').textContent=`Loading ${map.name} · ${completed} / ${maps.length*6} screenshots`;
        try{
          const loaded=await adapter.load(map.id,settings);
          if(cancelled)break;
          if(!loaded)throw new Error('Map load did not finish.');
          const plan=clueCapturePlan({...settings,mapId:map.id,wallIds:loaded.wallIds,box:loaded.box,aspect:width/height});
          const pending=[];
          for(const clue of plan.clues){
            if(cancelled)break;
            $('batch-status').textContent=`${map.name} · capturing clue ${clue.stage} / 6`;
            pending.push({clue,image:await adapter.capture(clue,settings)});
            $('batch-progress').value=completed+pending.length;
          }
          if(cancelled)break;
          if(!zip.canAdd(pending.reduce((sum,item)=>sum+item.image.size,0)+2*1024*1024,6))throw new Error('Archive memory limit reached. Download this batch and select fewer maps for the next one.');
          const folder=`${safeCaptureName(map.name)}-${safeCaptureName(map.id)}`;
          for(const {clue,image} of pending)await zip.add(`${folder}/clue-${String(clue.stage).padStart(2,'0')}.png`,image);
          manifest.maps.push({...loaded,groups:plan.groups,clues:plan.clues.map(clue=>({...clue,file:`${folder}/clue-${String(clue.stage).padStart(2,'0')}.png`}))});
          completed+=6;
        }catch(error){
          if(cancelled)break;
          manifest.errors.push({id:map.id,name:map.name,error:error.message});
          if(error.message.includes('memory limit'))break;
        }
      }
    }catch(error){manifest.errors.push({error:error.message});}
    finally{
      manifest.cancelled=cancelled;$('cancel-batch').disabled=true;$('batch-status').textContent='Restoring your original map and camera…';
      try{await adapter.restore(saved);}
      catch(error){manifest.errors.push({error:'View restore failed: '+error.message});}
      $('batch-progress').value=completed;
    }
    // Keep completed maps as a downloadable result even after cancellation/failure.
    try{
      await zip.add('manifest.json',new Blob([JSON.stringify(manifest,null,2)],{type:'application/json'}));
      downloadBlob=zip.finish();downloadUrl=URL.createObjectURL(downloadBlob);
      $('batch-save-local').classList.remove('hidden');
      const link=$('batch-download');link.href=downloadUrl;link.download=`portal-atlas-clues-${safeCaptureName(seed)}.zip`;link.classList.remove('hidden');
      $('batch-status').textContent=`${cancelled?'Cancelled':'Finished'} · ${manifest.maps.length} / ${maps.length} maps · ${completed} screenshots ready.`;
      $('batch-report').textContent=manifest.errors.length?manifest.errors.map(error=>`${error.name||'Batch'}: ${error.error}`).join('\n'):'Download the ZIP and review the images. Nothing was published to Portle.';
    }catch(error){$('batch-status').textContent='Could not finalize ZIP: '+error.message;}
    finally{adapter.setRunning(false);running=false;$('batch-settings').disabled=false;$('close-batch').disabled=false;summary();}
  };
}
