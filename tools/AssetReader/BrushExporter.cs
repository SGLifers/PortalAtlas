using CUE4Parse.FileProvider;
using CUE4Parse.UE4.Assets.Exports;
using CUE4Parse.UE4.Assets.Exports.Component;
using CUE4Parse.UE4.Objects.UObject;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

public static class BrushExporter
{
    public static void Add(IEnumerable<UObject> exports,string package,List<object> rows,List<object> errors)
    {
        foreach(var actor in exports.Where(o=>o.ExportType.Contains("BlockingVolume")))
        {
            try {
                var brush=actor.GetOrDefault<FPackageIndex>("BrushComponent")?.Load<UBrushComponent>()
                    ?? actor.GetOrDefault<FPackageIndex>("RootComponent")?.Load<UBrushComponent>();
                if(brush is null)throw new InvalidDataException("No blocking brush component");
                var body=brush.GetBodySetup() ?? throw new InvalidDataException("No blocking brush body setup");
                rows.Add(new { package,name=actor.GetPathName(),transform=brush.GetAbsoluteTransform(),
                    collision=brush.GetOrDefault<object>("BodyInstance"),body=JToken.FromObject(body),
                    enabled=actor.GetOrDefault<bool>("bActorEnableCollision",true) });
            } catch(Exception e){errors.Add(new { path=package,blockingVolume=actor.GetPathName(),error=e.Message });}
        }
    }
    public static void Enrich(DefaultFileProvider provider,string feature,string output)
    {
        PropertyUtil.SearchPropertyInTemplate=true;
        var file=Path.Combine(output,feature+".json");var manifest=JObject.Parse(File.ReadAllText(file));
        var rows=new List<object>();var errors=new List<object>();
        foreach(var p in manifest["packages"]!.OfType<JObject>())
        {
            var cached=Path.Combine(output,"packages",p["id"]!.Value<string>()+".json");
            if(!File.ReadAllText(cached).Contains("BlockingVolume"))continue;
            var path=p["path"]!.Value<string>()!;
            try {Add(provider.LoadPackage(path).GetExports(),path,rows,errors);}
            catch(Exception e){errors.Add(new { path,blockingVolume="package",error=e.Message });}
        }
        manifest["blockingVolumes"]=JArray.FromObject(rows);manifest["blockingErrors"]=JArray.FromObject(errors);manifest["blockingVersion"]=1;
        File.WriteAllText(file,manifest.ToString(Formatting.Indented));
        Console.WriteLine(JsonConvert.SerializeObject(new { feature,blockingVolumes=rows.Count,errors }));
    }
}
