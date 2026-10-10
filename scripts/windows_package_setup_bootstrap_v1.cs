// Inno's extraction directory must inherit G: before its first instruction runs.
using System;
using System.IO;
using System.Reflection;
using System.Diagnostics;
using System.Security.Cryptography;
using System.Text;
using System.Windows.Forms;
using System.Web.Script.Serialization;
using System.Collections.Generic;
using System.Net.Sockets;

internal static class PackageSetup {
    const string PayloadSha = "@PAYLOAD_SHA@";
    const string ContentManifestSha = "@CONTENT_MANIFEST_SHA@";
    const string Release = "@RELEASE@";
    const string ProgramRoot = @"@PROGRAM_ROOT@";
    static string Quote(string s) {
        var b = new StringBuilder("\""); int slashes = 0;
        foreach (char c in s) {
            if (c == '\\') { slashes++; continue; }
            if (c == '"') { b.Append('\\', slashes * 2 + 1); b.Append(c); }
            else { b.Append('\\', slashes); b.Append(c); }
            slashes = 0;
        }
        b.Append('\\', slashes * 2); return b.Append('"').ToString();
    }
    static string GPath(string value) {
        string p = Path.GetFullPath(value).TrimEnd('\\');
        if (!p.StartsWith(@"G:\", StringComparison.OrdinalIgnoreCase)) throw new Exception("G_DRIVE_REQUIRED");
        // Reject redirected directories; no writes through a junction to a source root.
        for (string q = p; !String.IsNullOrEmpty(q); q = Path.GetDirectoryName(q))
            if (Directory.Exists(q) && (File.GetAttributes(q) & FileAttributes.ReparsePoint) != 0)
                throw new Exception("REDIRECTED_DIRECTORY_FORBIDDEN");
        return p;
    }
    static bool Inside(string p, string root) {
        root = Path.GetFullPath(root).TrimEnd('\\');
        return p.Equals(root, StringComparison.OrdinalIgnoreCase) || p.StartsWith(root + "\\", StringComparison.OrdinalIgnoreCase);
    }
    static string FileSha(string p) {
        using (var hash = SHA256.Create()) using (var stream = File.OpenRead(p))
            return BitConverter.ToString(hash.ComputeHash(stream)).Replace("-", "").ToLowerInvariant();
    }
    [STAThread] static int Main(string[] args) {
        string temporary = null; bool silent = false; bool diagnosticRootVerified = false;
        try {
            string workspace = GPath(@"G:\codex work\大A交易");
            string target = GPath(Path.Combine(ProgramRoot, Release));
            var flags = new List<string>();
            foreach (string a in args) {
                string u = a.ToUpperInvariant();
                if (u == "/SILENT" || u == "/VERYSILENT") { silent = true; flags.Add(a); }
                else if (u == "/SUPPRESSMSGBOXES" || u == "/NORESTART") flags.Add(a);
                else if (u.StartsWith("/DIR=")) target = GPath(a.Substring(5));
                else if (u.StartsWith("/WORKSPACE=")) workspace = GPath(a.Substring(11));
                else if (u == "/TASKS=AUTOLOGIN" || u == "/TASKS=" || u == "/MERGETASKS=AUTOLOGIN") flags.Add(a);
                else throw new Exception("UNSUPPORTED_SETUP_ARGUMENT:" + a);
            }
            if (!Inside(target, ProgramRoot) || target.Equals(ProgramRoot, StringComparison.OrdinalIgnoreCase)
                || Inside(target, workspace) || Inside(workspace, target)) throw new Exception("SEPARATE_VERSION_DIRECTORY_REQUIRED");
            foreach (string name in new [] { "config/dm01_go_forward_runtime_contract_r4r1.json", "data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json", "data/v4/V4_DATA_ACCEPTED_HEAD.json" })
                if (!File.Exists(Path.Combine(workspace, name))) throw new Exception("VERIFIED_EXISTING_WORKSPACE_REQUIRED:" + name);
            var json = new JavaScriptSerializer();
            var contract = json.Deserialize<Dictionary<string, object>>(File.ReadAllText(Path.Combine(workspace, "config/dm01_go_forward_runtime_contract_r4r1.json")));
            var sources = new List<string> { @"D:\new_tdx" };
            object roots;
            if (contract.TryGetValue("read_only_tdx_roots", out roots))
                foreach (object item in (System.Collections.IEnumerable)roots) sources.Add(Convert.ToString(item));
            foreach (string source in sources)
                if (Inside(target, source) || Inside(source, target) || Inside(workspace, source)
                    || Inside(Path.Combine(workspace,"runtime/desktop/app.lock"),source)
                    || Inside(@"G:\codex_tmp", source) || Inside(source,@"G:\codex_tmp"))
                    throw new Exception("READ_ONLY_SOURCE_OVERLAP");
            GPath(@"G:\codex_tmp"); diagnosticRootVerified = true;
            string attestation = Path.Combine(workspace,"runtime/r4_product_loaded_modules.json");
            if (File.Exists(attestation)) {
                var prior = json.Deserialize<Dictionary<string,object>>(File.ReadAllText(attestation));
                if (GPath(Convert.ToString(prior["repo_root"])).Equals(workspace,StringComparison.OrdinalIgnoreCase)) {
                    Process legacy = null;
                    try { legacy = Process.GetProcessById(Convert.ToInt32(prior["pid"])); } catch (ArgumentException) { }
                    if (legacy != null) using (legacy) {
                        var observed=DateTime.Parse(Convert.ToString(prior["startup_time"])).ToUniversalTime();
                        var born=legacy.StartTime.ToUniversalTime();
                        if ((observed-born).TotalSeconds>=0 && (observed-born).TotalSeconds<120 &&
                            Path.GetFullPath(legacy.MainModule.FileName).Equals(Path.GetFullPath(Convert.ToString(prior["python_executable"])),StringComparison.OrdinalIgnoreCase))
                            throw new Exception("ATTESTED_LEGACY_WORKSPACE_WRITER_MUST_EXIT");
                    }
                }
            }
            string lockPath = Path.Combine(workspace, "runtime/desktop/app.lock");
            if (!File.Exists(lockPath)) {
                // First migration: the pre-lock legacy service must be explicitly stopped.
                bool occupied = false;
                using (var socket = new TcpClient()) {
                    try {
                        if (!socket.ConnectAsync("127.0.0.1", 28765).Wait(1500)) throw new Exception("LEGACY_PORT_VERIFICATION_TIMEOUT");
                        occupied = socket.Connected;
                    } catch (AggregateException e) {
                        var failure = e.GetBaseException() as SocketException;
                        if (failure == null || failure.SocketErrorCode != SocketError.ConnectionRefused) throw;
                    }
                }
                if (occupied) throw new Exception("LEGACY_SERVICE_MUST_EXIT_BEFORE_FIRST_INSTALL");
                Directory.CreateDirectory(Path.GetDirectoryName(lockPath));
                try { using (var stream = new FileStream(lockPath, FileMode.CreateNew, FileAccess.Write, FileShare.None)) stream.WriteByte(48); }
                catch (IOException) { if (!File.Exists(lockPath)) throw; }
            }
            temporary = GPath(Path.Combine(@"G:\codex_tmp\package_setup", Guid.NewGuid().ToString("N")));
            Directory.CreateDirectory(temporary);
            string core = Path.Combine(temporary, "setup-core.exe");
            using (var source = Assembly.GetExecutingAssembly().GetManifestResourceStream("setup-core"))
            using (var output = File.Create(core)) source.CopyTo(output);
            using (var hash = SHA256.Create()) using (var stream = File.OpenRead(core))
                if (BitConverter.ToString(hash.ComputeHash(stream)).Replace("-", "").ToLowerInvariant() != PayloadSha)
                    throw new Exception("SETUP_PAYLOAD_SHA_MISMATCH");
            flags.Add("/DIR=" + target); flags.Add("/WORKSPACE=" + workspace);
            flags.Add("/LOG=" + Path.Combine(temporary, "install.log"));
            var launch = new ProcessStartInfo(core, String.Join(" ", flags.ConvertAll(Quote).ToArray()));
            launch.UseShellExecute = false; launch.CreateNoWindow = true; launch.WorkingDirectory = temporary;
            launch.EnvironmentVariables["TMP"] = temporary; launch.EnvironmentVariables["TEMP"] = temporary; launch.EnvironmentVariables["TMPDIR"] = temporary;
            using (var process = Process.Start(launch)) {
                process.WaitForExit();
                if (process.ExitCode != 0) return process.ExitCode;
            }
            string listing = Path.Combine(target, "PACKAGE_FILES_MANIFEST.json");
            if (FileSha(listing) != ContentManifestSha) throw new Exception("INSTALLED_CONTENT_MANIFEST_CHANGED");
            var files = json.Deserialize<Dictionary<string,object>>(File.ReadAllText(listing));
            foreach (var value in (System.Collections.IEnumerable)files["files"]) {
                var item = (Dictionary<string,object>)value;
                string name = GPath(Path.Combine(target,Convert.ToString(item["path"])));
                if (!Inside(name,target) || FileSha(name) != Convert.ToString(item["sha256"]))
                    throw new Exception("INSTALLED_PROGRAM_FILE_SHA_MISMATCH:" + item["path"]);
            }
            File.WriteAllText(Path.Combine(temporary,"complete-program-verified.log"),"All installed runtime files match the S1-bound package manifest.");
            return 0;
        } catch (Exception e) {
            if (!silent) MessageBox.Show("安装未执行：" + e.Message, "大A交易", MessageBoxButtons.OK, MessageBoxIcon.Error);
            // A missing G: must never trigger a C: fallback.
            if (diagnosticRootVerified && Directory.Exists(@"G:\codex_tmp")) File.AppendAllText(@"G:\codex_tmp\package_setup_errors.log", DateTime.UtcNow.ToString("o") + " " + e.Message + Environment.NewLine);
            return 2;
        } finally {
            // Preserve G: setup logs and payload for diagnosis; no recursive cleanup or workspace deletion.
        }
    }
}
