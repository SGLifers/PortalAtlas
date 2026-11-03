using System.Security.Cryptography;
using System.Text;
using CUE4Parse.FileProvider;
using CUE4Parse.UE4.Assets.Exports.StaticMesh;
using CUE4Parse.UE4.Assets.Exports;
using CUE4Parse.UE4.Assets.Exports.Component.StaticMesh;
using CUE4Parse.UE4.Assets.Exports.Component;
using CUE4Parse.UE4.Objects.UObject;
using CUE4Parse.UE4.Objects.Core.Math;
using CUE4Parse.UE4.Assets.Exports.FastGeoStreaming;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

public static class FeatureExporter
{
    public static string Id(string path) => Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(path))).ToLowerInvariant()[..20];
    public static void Run(DefaultFileProvider provider, string feature, string output)
    {
        Directory.CreateDirectory(output);
        Directory.CreateDirectory(Path.Combine(output, "packages"));
        Directory.CreateDirectory(Path.Combine(output, "meshes"));
        var packages = provider.Files.Keys.Where(k => k.Contains($"/{feature}/",StringComparison.OrdinalIgnoreCase) && k.EndsWith(".umap",StringComparison.OrdinalIgnoreCase)).Order().ToArray();
        var meshPaths = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var loadedMeshes = new Dictionary<string,UStaticMesh>(StringComparer.OrdinalIgnoreCase);
        var manifest = new List<object>();
        var errors = new List<object>();
        var mappingPath=Environment.GetEnvironmentVariable("ATLAS_MAPPING_FILE");
        var schemaHash=mappingPath is null ? "none" : Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(mappingPath)));
        var components = new List<object>();
        var walls = new List<object>();
        PropertyUtil.SearchPropertyInTemplate = true;
        foreach (var path in packages)
        {
            var id = Id(path);
            var file = Path.Combine(output,"packages",id+".json");
            try
            {
                var exports = provider.LoadPackage(path).GetExports().ToArray();
                var json = JsonConvert.SerializeObject(exports);
                File.WriteAllText(file,json);
                foreach (var actor in exports.Where(o => o.ExportType.Contains("PortalWall") && !o.ExportType.Contains("Component") && !o.ExportType.Contains("Visuals")))
                {
                    try {
                        var root = actor.GetOrDefault<FPackageIndex>("Mesh")?.Load<USceneComponent>();
                        if (root is null) root = actor.GetOrDefault<FPackageIndex>("RootComponent")?.Load<USceneComponent>();
                        if (root is null) continue;
                        var values = new Dictionary<string,object?>();
                        foreach (var key in new [] { "bValidForPlayer", "bValidForAI", "bIsDoubleSided", "bLaunchPortalWall", "bRequireMinSpeedForLaunch", "LaunchSpeed", "MinSpeedToLaunch", "WallOrigin", "WallScale", "WallRotation" })
                            if (actor.TryGetValue<object>(out var value,key)) values[key]=value;
                        walls.Add(new { id=Id(actor.GetPathName()), package=path,
                            name=actor.Name, type=actor.ExportType, component=root.GetPathName(),
                            transform=root.GetAbsoluteTransform(), properties=values });
                    } catch (Exception e) { errors.Add(new { path, wall=actor.Name, error=e.Message }); }
                }
                foreach (var obj in exports.OfType<UStaticMeshComponent>())
                {
                    try
                    {
                        var mesh = obj.GetLoadedStaticMesh();
                        if (mesh is null) continue;
                        var meshPath = mesh.GetPathName().Split('.')[0];
                        meshPaths.Add(meshPath);
                        loadedMeshes[meshPath]=mesh;
                        components.Add(new { package=path, name=obj.GetPathName(), type=obj.ExportType,
                            mesh=Id(meshPath), meshPath,
                            transform=obj.GetAbsoluteTransform(),
                            instances=obj is UInstancedStaticMeshComponent ism ? ism.PerInstanceSMData : null,
                            collisionEnabled=obj.GetOrDefault<object>("BodyInstance"),
                            visible=!obj.GetOrDefault<bool>("bHiddenInGame") });
                    }
                    catch (Exception e) { errors.Add(new { path, component=obj.Name, error=e.Message }); }
                }
                foreach (var container in exports.OfType<UFastGeoContainer>())
                {
                    foreach (var cluster in container.ComponentClusters ?? [])
                    foreach (var component in cluster.StaticMeshComponents.Cast<FFastGeoStaticMeshComponentBase>().Concat(cluster.InstancedStaticMeshComponents))
                    {
                        try {
                            var mesh=component.SceneProxyDesc.StaticMeshSceneProxyDesc.StaticMesh.Load<UStaticMesh>();
                            if (mesh is null) continue;
                            var meshPath=mesh.GetPathName().Split('.')[0];
                            meshPaths.Add(meshPath);loadedMeshes[meshPath]=mesh;
                            components.Add(new { package=path,
                                name=container.GetPathName()+":"+cluster.Name+":"+component.ComponentIndex,
                                type="FastGeoStaticMeshComponent",mesh=Id(meshPath),meshPath,
                                transform=component.WorldTransform,
                                instances=component is FFastGeoInstancedStaticMeshComponent ism ? ism.PerInstanceSMData : null,
                                collisionEnabled=component.BodyInstance,visible=component.bVisible });
                        } catch (Exception e) { errors.Add(new { path, fastGeo=component.ComponentIndex,error=e.Message }); }
                    }
                }
                var array = JArray.Parse(json);
                foreach (var obj in array.Descendants().OfType<JObject>())
                {
                    var name = obj["ObjectName"]?.Value<string>();
                    var reference = obj["ObjectPath"]?.Value<string>();
                    if (name?.StartsWith("StaticMesh'") != true || reference is null) continue;
                    var dot = reference.LastIndexOf('.');
                    meshPaths.Add(dot > 0 ? reference[..dot] : reference);
                }
                manifest.Add(new { path, id, exports = array.Count });
                Console.Error.WriteLine($"PACKAGE {manifest.Count}/{packages.Length} {path}");
            }
            catch (Exception e) { errors.Add(new { path, error=e.Message }); }
        }
        var meshes = new List<object>();
        foreach (var path in meshPaths.Order())
        {
            var id = Id(path);
            var metaFile = Path.Combine(output,"meshes",id+".json");
            try
            {
                if (File.Exists(metaFile)) {
                    var cached=JObject.Parse(File.ReadAllText(metaFile));
                    if (cached["schemaHash"]?.Value<string>()==schemaHash) { meshes.Add(cached); continue; }
                }
                var mesh = loadedMeshes.TryGetValue(path,out var resolvedMesh) ? resolvedMesh : provider.LoadPackage(path).GetExports().OfType<UStaticMesh>().FirstOrDefault();
                if (mesh is null) throw new InvalidDataException("No static mesh export");
                var lod = mesh.RenderData?.LODs?.FirstOrDefault(l => l.PositionVertexBuffer?.Verts.Length>0 && l.IndexBuffer?.Buffer?.Length>0);
                if (lod is null) throw new InvalidDataException("No readable conventional mesh LOD");
                var verts = lod.PositionVertexBuffer!.Verts;
                var indices = lod.IndexBuffer!.Buffer!;
                if (verts.Any(v => !float.IsFinite(v.X)||!float.IsFinite(v.Y)||!float.IsFinite(v.Z)) || indices.Any(i=>i>=verts.Length)) throw new InvalidDataException("Invalid vertex/index data");
                using (var writer = new BinaryWriter(File.Create(Path.Combine(output,"meshes",id+".bin"))))
                {
                    writer.Write(verts.Length); writer.Write(indices.Length);
                    foreach (var v in verts) { writer.Write(v.X);writer.Write(v.Y);writer.Write(v.Z); }
                    foreach (var index in indices) writer.Write(index);
                }
                var body = mesh.BodySetup.Load();
                var meta = new { id, path, vertices=verts.Length, triangles=indices.Length/3,
                    bounds = mesh.RenderData?.Bounds,
                    body = body is null ? null : JToken.FromObject(body),
                    lod = Array.IndexOf(mesh.RenderData!.LODs!,lod), lodForCollision=mesh.LODForCollision,
                    collisionSource="render mesh; physics metadata retained separately", schemaHash };
                File.WriteAllText(metaFile,JsonConvert.SerializeObject(meta));
                meshes.Add(meta);
                Console.Error.WriteLine($"MESH {meshes.Count}/{meshPaths.Count} {path}");
            }
            catch (Exception e) { errors.Add(new { path, error=e.Message }); }
        }
        File.WriteAllText(Path.Combine(output,feature+".json"),JsonConvert.SerializeObject(new { feature, schemaHash, packages=manifest, components, walls, meshes, errors, diagnostics=DiagnosticSink.Events },Formatting.Indented));
        Console.WriteLine(JsonConvert.SerializeObject(new { feature, packages=manifest.Count, meshes=meshes.Count, errors=errors.Count }));
    }
}
