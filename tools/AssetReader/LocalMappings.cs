using CUE4Parse.MappingsProvider;

public class LocalMappings : JsonTypeMappingsProvider
{
    private string _path;
    public LocalMappings(string path) { _path = path; Reload(); }
    public override void Load(string path, StringComparer? comparer = null) { _path = path; Reload(); }
    public override void Load(byte[] bytes, StringComparer? comparer = null) => AddStructs(System.Text.Encoding.UTF8.GetString(bytes));
    public override void Reload() { AddStructs(File.ReadAllText(_path)); }
}
