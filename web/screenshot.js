// Capture only the map viewport. The WebGL frame must be copied synchronously
// after rendering, before the browser clears its non-preserved drawing buffer.
export function captureMapView({renderer,world,camera,labels}){
  const source=renderer.domElement,rect=source.getBoundingClientRect();
  if(!source.width||!source.height||!rect.width||!rect.height)throw new Error('The map view is not ready.');
  if(renderer.getContext().isContextLost())throw new Error('The graphics context was lost. Reload the map and try again.');
  const image=document.createElement('canvas');image.width=source.width;image.height=source.height;
  const ctx=image.getContext('2d');if(!ctx)throw new Error('PNG capture is unavailable in this browser.');
  ctx.scale(image.width/rect.width,image.height/rect.height);
  // Match .viewport-section's radial background; the WebGL canvas is transparent.
  const w=rect.width,h=rect.height,cx=w*.45,cy=h*.4,rx=Math.max(cx,w-cx)*Math.SQRT2,ry=Math.max(cy,h-cy)*Math.SQRT2;
  ctx.save();ctx.translate(cx,cy);ctx.scale(rx,ry);
  const background=ctx.createRadialGradient(0,0,0,0,0,1);background.addColorStop(0,'#1d282a');background.addColorStop(.7,'#10171d');
  ctx.fillStyle=background;ctx.fillRect(-cx/rx,-cy/ry,w/rx,h/ry);ctx.restore();
  renderer.render(world,camera);
  ctx.drawImage(source,0,0,w,h);
  const containerStyle=getComputedStyle(labels);
  if(containerStyle.display!=='none'&&containerStyle.visibility!=='hidden'){
    for(const label of labels.children){
      const style=getComputedStyle(label),box=label.getBoundingClientRect();
      if(style.display==='none'||style.visibility==='hidden'||!box.width||!box.height)continue;
      const x=box.left-rect.left,y=box.top-rect.top;
      if(x+box.width<0||y+box.height<0||x>w||y>h)continue;
      ctx.save();ctx.globalAlpha=Number(style.opacity);
      const border=parseFloat(style.borderTopWidth)||0;
      ctx.beginPath();ctx.roundRect(x+border/2,y+border/2,Math.max(0,box.width-border),Math.max(0,box.height-border),parseFloat(style.borderTopLeftRadius)||0);
      ctx.fillStyle=style.backgroundColor;ctx.fill();
      if(border){ctx.lineWidth=border;ctx.strokeStyle=style.borderTopColor;ctx.stroke();}
      ctx.font=style.font;ctx.fillStyle=style.color;ctx.textAlign='center';ctx.textBaseline='middle';
      ctx.shadowColor='#000';ctx.shadowOffsetY=1;ctx.shadowBlur=3;
      ctx.fillText(label.textContent,x+box.width/2,y+box.height/2);ctx.restore();
    }
  }
  return new Promise((resolve,reject)=>image.toBlob(blob=>blob?resolve(blob):reject(new Error('Could not encode the screenshot.')),'image/png'));
}

export function screenshotFilename(map,view,date=new Date()){
  const name=String(map||'map').replace(/^MAP_/,'').replace(/[^A-Za-z0-9_-]+/g,'-').slice(0,80)||'map';
  return `portal-atlas-${name}-${view==='top'?'top':'3d'}-${date.toISOString().replace(/[:.]/g,'-')}.png`;
}

export function downloadScreenshot(blob,filename){
  const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download=filename;
  document.body.append(link);link.click();link.remove();
  // Keep the URL alive while the browser begins the download, then free it.
  setTimeout(()=>URL.revokeObjectURL(url),60000);
}
