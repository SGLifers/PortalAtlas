using CUE4Parse.FileProvider;
using CUE4Parse.UE4.Assets.Exports;
using CUE4Parse.UE4.Assets.Exports.Component.Landscape;
using CUE4Parse.UE4.Assets.Exports.Texture;
using CUE4Parse.UE4.Objects.Core.Math;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

public static class TerrainExporter
{
    public static void Add(IEnumerable<UObject> exports, string package, string output,
        List<object> components, List<object> meshes, List<object> errors)
    {
        foreach (var component in exports.OfType<ULandscapeComponent>())
        {
            try
            {
                if (component.GetOrDefault<object>("XYOffsetmapTexture") is not null)
                    throw new InvalidDataException("Landscape XY offsets are not supported");
                int level=component.GetOrDefault<int>("CollisionMipLevel");
                var texture=component.GetHeightmap() ?? throw new InvalidDataException("Missing landscape heightmap");
                var (height,width,heightData)=Read(texture,level);
                int subsectionVerts=(component.SubsectionSizeQuads+1)>>level;
                int quads=(subsectionVerts-1)*component.NumSubsections;
                if (quads<1 || quads>2048) throw new InvalidDataException("Invalid landscape dimensions");
                int offsetX=(int)(width*component.HeightmapScaleBias.Z),offsetY=(int)(height*component.HeightmapScaleBias.W);
                int Texel(int x) => x==0 ? 0 : (x-1)/(subsectionVerts-1)*subsectionVerts+(x-1)%(subsectionVerts-1)+1;
                byte Sample(byte[] data,int stride,int x,int y,int channel) => data[((y*stride+x)*4)+channel];
                byte[]? visibility=null;int visibilityWidth=0,visibilityX=0,visibilityY=0,visibilityChannel=0;
                foreach (var allocation in component.GetWeightmapLayerAllocations())
                {
                    if (!allocation.GetLayerName().Contains("Visibility",StringComparison.OrdinalIgnoreCase)) continue;
                    var weights=component.GetWeightmapTextures();
                    if (allocation.WeightmapTextureIndex>=weights.Length || allocation.WeightmapTextureChannel>3)
                        throw new InvalidDataException("Invalid landscape visibility allocation");
                    var (vh,vw,data)=Read(weights[allocation.WeightmapTextureIndex],level);
                    visibility=data;visibilityWidth=vw;visibilityX=(int)(vw*component.WeightmapScaleBias.Z);visibilityY=(int)(vh*component.WeightmapScaleBias.W);
                    visibilityChannel=new[]{2,1,0,3}[allocation.WeightmapTextureChannel];
                }
                var vertices=new List<FVector>((quads+1)*(quads+1));
                float minZ=float.MaxValue,maxZ=float.MinValue;
                for (int y=0;y<=quads;y++) for(int x=0;x<=quads;x++)
                {
                    int tx=offsetX+Texel(x),ty=offsetY+Texel(y);
                    if(tx>=width || ty>=height) throw new InvalidDataException("Landscape texel exceeds heightmap");
                    float z=((Sample(heightData,width,tx,ty,2)<<8)+Sample(heightData,width,tx,ty,1)-32768)/128f;
                    vertices.Add(new FVector(x*(float)component.ComponentSizeQuads/quads,y*(float)component.ComponentSizeQuads/quads,z));
                    minZ=Math.Min(minZ,z);maxZ=Math.Max(maxZ,z);
                }
                // Height decode must agree with the independently serialized bounds.
                if(minZ<component.CachedLocalBox.Min.Z-2 || maxZ>component.CachedLocalBox.Max.Z+2)
                    throw new InvalidDataException($"Landscape height bounds mismatch: {minZ}..{maxZ}");
                var indices=new List<uint>();int hidden=0;
                for(int y=0;y<quads;y++) for(int x=0;x<quads;x++)
                {
                    // Use the cooked collision mip's visibility channel. Any hole
                    // corner removes the cell, avoiding fabricated floor support.
                    bool hole=visibility is not null && new[]{(x,y),(x+1,y),(x,y+1),(x+1,y+1)}.Any(p=>Sample(visibility,visibilityWidth,visibilityX+Texel(p.Item1),visibilityY+Texel(p.Item2),visibilityChannel)>170);
                    if(hole){hidden++;continue;}
                    uint a=(uint)(y*(quads+1)+x),b=a+1,c=a+(uint)quads+1,d=c+1;
                    indices.AddRange(new[]{a,d,b,a,c,d});
                }
                var id=FeatureExporter.Id(component.GetPathName()+":collision-heightfield-v1");
                using(var writer=new BinaryWriter(File.Create(Path.Combine(output,"meshes",id+".bin"))))
                {
                    writer.Write(vertices.Count);writer.Write(indices.Count);
                    foreach(var v in vertices){writer.Write(v.X);writer.Write(v.Y);writer.Write(v.Z);}
                    foreach(var i in indices)writer.Write(i);
                }
                var meta=new { id,path=component.GetPathName(),vertices=vertices.Count,triangles=indices.Count/3,
                    lod=level,lodForCollision=level,collisionSource="landscape heightmap at serialized collision mip, visibility holes",terrain=true,
                    hiddenCells=hidden,body=(object?)null };
                File.WriteAllText(Path.Combine(output,"meshes",id+".json"),JsonConvert.SerializeObject(meta));
                meshes.Add(meta);
                components.Add(new { package,name=component.GetPathName(),type="LandscapeHeightfield",mesh=id,meshPath=component.GetPathName(),
                    transform=component.GetAbsoluteTransform(),instances=(object?)null,collisionEnabled=new { CollisionProfileName="BlockAll" },visible=true });
            }
            catch(Exception e){errors.Add(new { path=package,terrain=component.GetPathName(),error=e.Message });}
        }
    }

    static (int height,int width,byte[] data) Read(UTexture2D texture,int level)
    {
        if(texture.Format!=EPixelFormat.PF_B8G8R8A8) throw new InvalidDataException("Unsupported landscape texture format "+texture.Format);
        var mip=texture.GetMip(level) ?? throw new InvalidDataException("Missing landscape collision mip");
        var data=mip.BulkData?.Data ?? throw new InvalidDataException("Missing landscape texture bulk data");
        if(data.Length!=mip.SizeX*mip.SizeY*4) throw new InvalidDataException("Unexpected landscape texture length");
        return(mip.SizeY,mip.SizeX,data);
    }

    public static void Enrich(DefaultFileProvider provider,string feature,string output)
    {
        var path=Path.Combine(output,feature+".json");var manifest=JObject.Parse(File.ReadAllText(path));
        var components=new List<object>();var meshes=new List<object>();var errors=new List<object>();
        foreach(var package in manifest["packages"]!.OfType<JObject>())
        {
            var name=package["path"]!.Value<string>()!;
            try {Add(provider.LoadPackage(name).GetExports(),name,output,components,meshes,errors);}
            catch(Exception e){errors.Add(new { path=name,terrain="package",error=e.Message });}
        }
        var oldComponents=(JArray)manifest["components"]!;
        foreach(var c in oldComponents.OfType<JObject>().Where(c=>c["type"]?.Value<string>()=="LandscapeHeightfield").ToArray()) c.Remove();
        var oldMeshes=(JArray)manifest["meshes"]!;
        foreach(var m in oldMeshes.OfType<JObject>().Where(m=>m["terrain"]?.Value<bool>()==true).ToArray())m.Remove();
        foreach(var c in components)oldComponents.Add(JObject.FromObject(c));
        foreach(var m in meshes)oldMeshes.Add(JObject.FromObject(m));
        manifest["terrainErrors"]=JArray.FromObject(errors);manifest["terrainVersion"]=1;
        File.WriteAllText(path,manifest.ToString(Formatting.Indented));
        Console.WriteLine(JsonConvert.SerializeObject(new { feature,terrain=components.Count,errors }));
    }
}
