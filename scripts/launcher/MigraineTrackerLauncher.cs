using System;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Windows.Forms;

internal static class MigraineTrackerLauncher
{
    [DllImport("shell32.dll", SetLastError = true)]
    private static extern int SetCurrentProcessExplicitAppUserModelID(string appId);

    [STAThread]
    private static void Main()
    {
        SetCurrentProcessExplicitAppUserModelID("MigraineTracker.App");

        string projectDirectory = AppDomain.CurrentDomain.BaseDirectory;
        string launcherScript = Path.Combine(projectDirectory, "scripts", "launch_app.ps1");

        if (!File.Exists(launcherScript))
        {
            MessageBox.Show(
                "Das Startskript des Kopfschmerz-Trackers wurde nicht gefunden.",
                "Kopfschmerz-Tracker",
                MessageBoxButtons.OK,
                MessageBoxIcon.Error);
            return;
        }

        var startInfo = new ProcessStartInfo
        {
            FileName = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.System),
                "WindowsPowerShell",
                "v1.0",
                "powershell.exe"),
            Arguments = string.Format(
                "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File \"{0}\"",
                launcherScript),
            WorkingDirectory = projectDirectory,
            UseShellExecute = false,
            CreateNoWindow = true,
            WindowStyle = ProcessWindowStyle.Hidden
        };

        try
        {
            Process.Start(startInfo);
        }
        catch (Exception exception)
        {
            MessageBox.Show(
                "Der Kopfschmerz-Tracker konnte nicht gestartet werden.\n\n" + exception.Message,
                "Kopfschmerz-Tracker",
                MessageBoxButtons.OK,
                MessageBoxIcon.Error);
        }
    }
}
