using CUE4Parse.MappingsProvider;

public class LocalMappings : JsonTypeMappingsProvider
{
    private string _path;
    public LocalMappings(string path) { _path = path; Reload(); }
    public override void Load(string path, StringComparer? comparer = null) { _path = path; Reload(); }
    public override void Load(byte[] bytes, StringComparer? comparer = null) => AddStructs(System.Text.Encoding.UTF8.GetString(bytes));
    public override void Reload() {
        AddStructs(File.ReadAllText(_path));
        var enums = Path.Combine(Path.GetDirectoryName(_path)!,Path.GetFileNameWithoutExtension(_path)+"-enums.json");
        if (File.Exists(enums)) {
            var nativeEnums=Newtonsoft.Json.JsonConvert.DeserializeObject<Dictionary<string,Dictionary<long,string>>>(File.ReadAllText(enums));
            foreach (var pair in nativeEnums!) MappingsForGame!.Enums[pair.Key]=pair.Value;
        }
    }
}
