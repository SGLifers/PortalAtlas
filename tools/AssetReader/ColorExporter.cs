using CUE4Parse.FileProvider;
using CUE4Parse.UE4.Assets.Exports;
using CUE4Parse.UE4.Assets.Exports.Component.StaticMesh;
using CUE4Parse.UE4.Assets.Exports.FastGeoStreaming;
using CUE4Parse.UE4.Assets.Exports.StaticMesh;
using CUE4Parse.UE4.Objects.UObject;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

/// <summary>Independent appearance sidecar: never changes collision meshes or graphs.</summary>
public static class ColorExporter
{
    static JToken? Property(JToken? value,string name) => (value as JObject)?.Properties()
        .FirstOrDefault(p=>p.Name==name || p.Name.StartsWith(name+"[",StringComparison.Ordinal))?.Value;
    static string? Reference(JToken? value)
    {
        if(value is not JObject)return null;
        var path=value?["ObjectPath"]?.Value<string>();
        var name=value?["ObjectName"]?.Value<string>()?.Split('\'').ElementAtOrDefault(1);
        return path is null ? null : path[..path.LastIndexOf('.')]+"."+(name ?? path[(path.LastIndexOf('.')+1)..]);
    }
    static string Normalize(string value)=>new(value.ToLowerInvariant().Where(char.IsLetterOrDigit).ToArray());
    static readonly string[] ColorNames=["basecolor","basecolour","albedo","diffusecolor","diffusecolour","color","colour","color1","colour1","basecolortint","basecolourtint","colortint","tintcolor","tint"];

    public static void Run(DefaultFileProvider provider,string map,string output)
    {
        if(!System.Text.RegularExpressions.Regex.IsMatch(map,@"^MAP_[A-Za-z0-9_]+$"))throw new InvalidDataException("Invalid map ID");
        var scene=JObject.Parse(File.ReadAllText(Path.Combine("data/scenes",map+".json")));
        var materials=new Dictionary<string,JObject>();
        var meshes=new Dictionary<string,object>();
        var components=new Dictionary<string,string?[]>();
        var errors=new List<object>();
        var assets=new Dictionary<string,JObject>();
        // Cooked GameFeature plugins are not all mounted under their short names
        // by the parser. Resolve their real archive paths without altering mounts.
        var aliases=new Dictionary<string,string>(StringComparer.OrdinalIgnoreCase);
        foreach(var file in provider.Files.Keys.Where(p=>p.EndsWith(".uasset")||p.EndsWith(".umap")).Order())
        {
            var match=System.Text.RegularExpressions.Regex.Match(file,@"/([^/]+)/Content/(.+)\.(?:uasset|umap)$");
            if(match.Success)aliases.TryAdd("/"+(match.Groups[1].Value=="PortalWars2"?"Game":match.Groups[1].Value)+"/"+match.Groups[2].Value,file);
        }
        CUE4Parse.UE4.Assets.IPackage Package(string path)=>provider.LoadPackage(aliases.TryGetValue(path,out var file)?file:path);
        JObject Asset(string reference)
        {
            if(assets.TryGetValue(reference,out var cached))return cached;
            var split=reference.IndexOf('.');var path=split<0?reference:reference[..split];var name=split<0?null:reference[(reference.LastIndexOf('.')+1)..];
            var exports=Package(path).GetExports().ToArray();
            var asset=exports.FirstOrDefault(o=>o.GetPathName()==reference) ?? exports.FirstOrDefault(o=>o.Name==name) ?? (name is null ? exports.First() : throw new InvalidDataException("Referenced export missing"));
            var json=JObject.FromObject(asset);assets[reference]=json;return json;
        }
        JObject? Color(string reference,HashSet<string> visited,int depth=0)
        {
            if(depth>12 || !visited.Add(reference))return null;
            var asset=Asset(reference);var properties=asset["Properties"];
            var vectors=Property(properties,"VectorParameterValues") as JArray ?? [];
            foreach(var key in ColorNames)
            foreach(var vector in vectors)
            {
                var info=Property(vector,"ParameterInfo");
                var name=Property(info,"Name")?.Value<string>() ?? Property(vector,"ParameterName")?.Value<string>() ?? "";
                var v=Property(vector,"ParameterValue");
                if(Normalize(name)!=key || v is not JObject)continue;
                var rgb=new[]{v["R"]?.Value<double>() ?? double.NaN,v["G"]?.Value<double>() ?? double.NaN,v["B"]?.Value<double>() ?? double.NaN};
                if(rgb.Any(c=>!double.IsFinite(c)||c<0))continue;
                return new JObject{["colorLinear"]=new JArray(rgb.Select(c=>Math.Min(c,1))),["sourceAsset"]=reference,["sourceParameter"]=name,["method"]="parameter"};
            }
            // Serialized material-layer order is retained. This is a representative
            // base-layer color, not evaluation of masks, textures, or shader code.
            var layerArrays=(properties as JObject)?.Descendants().OfType<JProperty>().Where(p=>p.Name=="Layers" || p.Name.StartsWith("Layers[")) ?? [];
            foreach(var array in layerArrays)
            foreach(var layer in array.Value as JArray ?? [])
            {
                var path=Reference(layer);if(path is null)continue;
                var result=Color(path,visited,depth+1);
                if(result is not null){result["method"]="layer-parameter";return result;}
            }
            var parent=Reference(Property(properties,"Parent"));
            return parent is null ? null : Color(parent,visited,depth+1);
        }
        string? Material(string? reference)
        {
            if(reference is null)return null;
            var id=FeatureExporter.Id(reference);
            if(materials.ContainsKey(id))return id;
            var record=new JObject{["id"]=id,["path"]=reference,["method"]="unresolved"};materials[id]=record;
            try
            {
                var color=Color(reference,new HashSet<string>());
                if(color is not null)foreach(var property in color.Properties())record[property.Name]=property.Value;
            }
            catch(Exception e){record["error"]=e.GetType().Name;record["note"]=e.Message;}
            return id;
        }
        foreach(var row in scene["meshes"]!)
        {
            var id=row["id"]!.Value<string>()!;var path=row["path"]!.Value<string>()!;
            if(row["viewProxy"]?.Value<bool>()==true)continue;
            try
            {
                var mesh=Package(path).GetExports().OfType<UStaticMesh>().First();
                var lodIndex=row["lod"]!.Value<int>();var lod=mesh.RenderData!.LODs![lodIndex];
                var json=JObject.FromObject(mesh);
                var slots=(Property(json["Properties"],"StaticMaterials") as JArray ?? []).Select(v=>Material(Reference(Property(v,"MaterialInterface")))).ToArray();
                // Some engine versions serialize slots natively rather than as properties.
                if(slots.Length==0)slots=mesh.Materials.Select(r=>Material(r?.Load()?.GetPathName())).ToArray();
                var indices=lod.IndexBuffer!.Buffer!.Length;
                if(indices!=row["triangles"]!.Value<int>()*3)throw new InvalidDataException("LOD does not match existing geometry");
                meshes[id]=new{slots,vertices=lod.PositionVertexBuffer!.Verts.Length,indexCount=indices,lod=lodIndex,
                    sections=lod.Sections.Select(s=>new{start=s.FirstIndex,count=s.NumTriangles*3,slot=s.MaterialIndex}).ToArray()};
            }
            catch(Exception e){errors.Add(new{mesh=id,path,error=e.GetType().Name});}
            if(meshes.Count%50==0)Console.Error.WriteLine($"COLOR MESHES {meshes.Count}/{scene["meshes"]!.Count()}");
        }
        foreach(var level in scene["source"]!["levels"]!)
        {
            try
            {
                foreach(var obj in Package(level.Value<string>()!).GetExports())
                {
                    if(obj is UStaticMeshComponent)
                    {
                        var json=JObject.FromObject(obj);
                        var refs=Property(json["Properties"],"OverrideMaterials") as JArray;
                        if(refs is not null)components[obj.GetPathName()]=refs.Select(r=>Material(Reference(r))).ToArray();
                    }
                    if(obj is UFastGeoContainer container)
                    foreach(var cluster in container.ComponentClusters ?? [])
                    foreach(var component in cluster.StaticMeshComponents.Cast<FFastGeoStaticMeshComponentBase>().Concat(cluster.InstancedStaticMeshComponents))
                        if(component.OverrideMaterials.Length>0)
                            components[container.GetPathName()+":"+cluster.Name+":"+component.ComponentIndex]=component.OverrideMaterials.Select(r=>Material(r.Load()?.GetPathName())).ToArray();
                }
            }
            catch(Exception e){errors.Add(new{level=level.Value<string>(),error=e.GetType().Name});}
        }
        var resolved=materials.Values.Count(m=>m["colorLinear"] is not null);
        var report=new{meshes=meshes.Count,materials=materials.Count,resolvedMaterials=resolved,unresolvedMaterials=materials.Count-resolved,componentOverrides=components.Count,errors=errors.Count};
        var result=new{format="portal-atlas-colors",version=1,map,sceneRevision=scene["revision"],
            description="Representative material parameter colors; textures, layer masks, vertex paint, shader switches and game lighting are not evaluated. Unresolved surfaces retain the neutral color.",
            materials,meshes,components,report,errors};
        Directory.CreateDirectory(output);var destination=Path.Combine(output,map+".json");
        File.WriteAllText(destination+".tmp",JsonConvert.SerializeObject(result));File.Move(destination+".tmp",destination,true);
        Console.WriteLine(JsonConvert.SerializeObject(report));
    }
}
