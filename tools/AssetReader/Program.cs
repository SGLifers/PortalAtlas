using CUE4Parse.Compression;
using CUE4Parse.Encryption.Aes;
using CUE4Parse.FileProvider;
using CUE4Parse.MappingsProvider.Usmap;
using CUE4Parse.UE4.Objects.Core.Misc;
using CUE4Parse.UE4.Versions;
using Newtonsoft.Json;
using Serilog;
using CUE4Parse.GameTypes.Splitgate2.Encryption.Aes;
using System.Buffers.Binary;

Log.Logger = new LoggerConfiguration().WriteTo.Console(standardErrorFromLevel:
    Serilog.Events.LogEventLevel.Verbose).WriteTo.Sink(new DiagnosticSink()).CreateLogger();
if (args.Length < 2) {
    Console.Error.WriteLine("AssetReader <paks> <list|dump|raw|scan-keys> [path/filter] [output]");
    return 2;
}
var paks = Path.GetFullPath(args[0]);
var command = args[1];
var filter = args.ElementAtOrDefault(2) ?? "";
var engine = Environment.GetEnvironmentVariable("ATLAS_ENGINE") is string e ? Enum.Parse<EGame>(e) : EGame.GAME_Splitgate2;
using var provider = new DefaultFileProvider(paks, SearchOption.TopDirectoryOnly,
    new VersionContainer(engine), StringComparer.OrdinalIgnoreCase);
provider.Initialize();
var keyFile = Environment.GetEnvironmentVariable("ATLAS_KEY_FILE");
var mappingFile = Environment.GetEnvironmentVariable("ATLAS_MAPPING_FILE");
if (!string.IsNullOrEmpty(mappingFile))
    provider.MappingsContainer = mappingFile.EndsWith(".json") ? new LocalMappings(mappingFile) : new FileUsmapTypeMappingsProvider(mappingFile);
if (!string.IsNullOrEmpty(keyFile))
    provider.SubmitKey(new FGuid(), new FAesKey(File.ReadAllText(keyFile).Trim()));
provider.Mount();
if (command == "check-key") {
    var candidate = new FAesKey(File.ReadAllText(filter).Trim());
    foreach (var target in provider.UnloadedVfs.Where(r => r.IsEncrypted && r.HasDirectoryIndex)) {
        var block = target.MountPointCheckBytes()[..16];
        File.WriteAllBytes("data/check-" + target.Name + ".bin", block);
        CustomAesKeyExpansion.DecryptWithRoundKeys(block,0,Aes1047Games.KeyExpansion(candidate.Key));
        Console.WriteLine(JsonConvert.SerializeObject(new { target = target.Name, firstBlock = Convert.ToHexString(block), valid = target.TestAesKey(candidate) }));
    }
    return 0;
}
if (command == "scan-memory") {
    var bytes = File.ReadAllBytes(filter);
    var target = provider.UnloadedVfs.Where(r => r.IsEncrypted && r.HasDirectoryIndex).OrderBy(r => r.Name.EndsWith(".pak") ? 0 : 1).First();
    var encrypted = target.MountPointCheckBytes()[..16];
    var pe = BitConverter.ToInt32(bytes, 60);
    var n = BitConverter.ToUInt16(bytes, pe + 6);
    var opt = BitConverter.ToUInt16(bytes, pe + 20);
    var key = new byte[32];
    var block = new byte[16];
    for (int s = 0; s < n; s++) {
        var h = pe + 24 + opt + s * 40;
        var name = System.Text.Encoding.ASCII.GetString(bytes, h, 8).TrimEnd('\0');
        if (name != ".rdata" && name != ".data") continue;
        var size = BitConverter.ToInt32(bytes, h + 16);
        var start = BitConverter.ToInt32(bytes, h + 20);
        Console.Error.WriteLine($"Scanning {name}: {size} bytes");
        for (int pos = start; pos < start + size - 32; pos += 1) {
            Array.Copy(bytes, pos, key, 0, 32);
            if (BitConverter.ToUInt64(key,0)==0 || BitConverter.ToUInt64(key,16)==0) continue;
            Array.Copy(encrypted, block, 16);
            CustomAesKeyExpansion.DecryptWithRoundKeys(block,0,Aes1047Games.KeyExpansion(key));
            int len = BitConverter.ToInt32(block);
            if (len is < 5 or > 256 || block[4] < 32 || block[4] > 126) continue;
            if (!target.TestAesKey(new FAesKey(key))) continue;
            File.WriteAllText(args[3], Convert.ToHexString(key));
            Console.WriteLine(JsonConvert.SerializeObject(new { success = true, offset = pos, section = name }));
            return 0;
        }
    }
    Console.WriteLine("{\"success\":false}");
    return 1;
}
if (command == "scan-keys") {
    var candidates = JsonConvert.DeserializeObject<string[]>(File.ReadAllText(filter))!;
    var target = provider.UnloadedVfs.Where(r => r.IsEncrypted && r.HasDirectoryIndex).OrderBy(r => r.Name.EndsWith(".pak") ? 0 : 1).First();
    var encrypted = target.MountPointCheckBytes()[..16];
    var block = new byte[16];
    using var aes = System.Security.Cryptography.Aes.Create();
    foreach (var key in candidates) {
        try {
            var candidate = new FAesKey(key);
            if (engine == EGame.GAME_Splitgate2) {
                Array.Copy(encrypted, block, 16);
                CustomAesKeyExpansion.DecryptWithRoundKeys(block,0,Aes1047Games.KeyExpansion(candidate.Key));
            } else {
                aes.Key = candidate.Key;
                aes.DecryptEcb(encrypted,block,System.Security.Cryptography.PaddingMode.None);
            }
            int len = BitConverter.ToInt32(block);
            if (len is < 5 or > 256 || block[4] < 32 || block[4] > 126) continue;
            if (target.TestAesKey(new FAesKey(key))) {
                provider.SubmitKey(new FGuid(), new FAesKey(key));
                var dest = args.ElementAtOrDefault(3) ?? "data/key.txt";
                File.WriteAllText(dest, key);
                Console.WriteLine(JsonConvert.SerializeObject(new { success = true,
                    files = provider.Files.Count, keyFile = dest }));
                return 0;
            }
        } catch { }
    }
    Console.WriteLine(JsonConvert.SerializeObject(new { success = false, count = candidates.Length }));
    return 1;
}
provider.PostMount();
if (command == "list") {
    var files = provider.Files.Keys.Where(k => k.Contains(filter, StringComparison.OrdinalIgnoreCase)).Order().ToArray();
    var json = JsonConvert.SerializeObject(new { count = files.Length, files }, Formatting.Indented);
    if (args.Length > 3) File.WriteAllText(args[3], json); else Console.WriteLine(json);
    return 0;
}
OodleHelper.Initialize(Path.GetFullPath(".tools/liboodle-data-shared.so"));
if (command == "export-feature") {
    FeatureExporter.Run(provider, filter, args[3]);
    return 0;
}
if (command == "raw") {
    File.WriteAllBytes(args[3], provider.SaveAsset(filter));
    return 0;
}
if (command == "dump") {
    var exports = provider.LoadPackage(filter).GetExports();
    var json = JsonConvert.SerializeObject(exports, Formatting.Indented);
    if (args.Length > 3) File.WriteAllText(args[3], json); else Console.WriteLine(json);
    return 0;
}
Console.Error.WriteLine("Unknown command");
return 2;
