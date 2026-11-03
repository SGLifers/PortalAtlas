using Serilog.Core;
using Serilog.Events;

public class DiagnosticSink : ILogEventSink
{
    public static List<object> Events = new();
    public void Emit(LogEvent logEvent) {
        if (logEvent.Level < LogEventLevel.Warning) return;
        lock (Events) Events.Add(new { level=logEvent.Level.ToString(), message=logEvent.RenderMessage() });
    }
}
