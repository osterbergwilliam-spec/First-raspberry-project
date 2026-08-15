#nullable enable
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;
using System.Threading;

namespace SmartLockSystem
{
    // ==========================================
    // DATA MODELS
    // ==========================================
    public class SystemState
    {
        public double Proximity { get; set; }
        public double Value { get; set; }
        public int FaceCount { get; set; }
        public string PersonName { get; set; } = string.Empty;
        public bool IsAuthorized { get; set; }
    }

    // ==========================================
    // ABSTRACTIONS
    // ==========================================
    public interface ILockAction
    {
        string ActionName { get; }
        void Execute();
    }

    public interface IInputProvider
    {
        SystemState GetCurrentState();
    }

        public class SimulatedAction : ILockAction
    {
        private readonly string _name;
        private readonly string _description;
        public string ActionName => _name;

        public SimulatedAction(string name, string description)
        {
            _name = name;
            _description = description;
        }

        public void Execute()
        {
            Console.WriteLine($"\n[HARDWARE] {ActionName}: {_description}");
        }
    }

    // ==========================================
    // INPUT PROVIDER (SOCKET)
    // ==========================================
    public class SocketInputProvider : IInputProvider
    {
        private readonly TcpListener _listener;
        private SystemState _lastState = new SystemState();
        
        public SocketInputProvider(int port = 9999)
        {
            _listener = new TcpListener(IPAddress.Loopback, port);
            _listener.Start();
            Console.WriteLine($"[SOCKET] Listening on port {port}");
            
            // Start listening thread
            new Thread(ListenForData) { IsBackground = true }.Start();
        }
        
        private void ListenForData()
        {
            while (true)
            {
                try
                {
                    using var client = _listener.AcceptTcpClient();
                    using var stream = client.GetStream();
                    
                    var buffer = new byte[1024];
                    var bytesRead = stream.Read(buffer, 0, buffer.Length);
                    
                    if (bytesRead > 0)
                    {
                        var json = Encoding.UTF8.GetString(buffer, 0, bytesRead);
                        _lastState = JsonSerializer.Deserialize<SystemState>(json, new JsonSerializerOptions { PropertyNameCaseInsensitive = true }) ?? new SystemState();
                        Console.WriteLine($"[SOCKET] Data received: {json}");
                    }
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"[SOCKET] Error: {ex.Message}");
                }
            }
        }
        
        public SystemState GetCurrentState()
        {
            return _lastState;
        }
    }

    // ==========================================
    // INPUT PROVIDER (JSON)
    // ==========================================
    public class JsonInputProvider : IInputProvider
    {
        private readonly string _filePath;
        public JsonInputProvider(string filePath) => _filePath = filePath;

        public SystemState GetCurrentState()
        {
            try
            {
                if (!File.Exists(_filePath)) return new SystemState { Proximity = 0, Value = -1 };
                string json = File.ReadAllText(_filePath);
                var options = new JsonSerializerOptions { PropertyNameCaseInsensitive = true };
                return JsonSerializer.Deserialize<SystemState>(json, options) ?? new SystemState();
            }
            catch { return new SystemState { Proximity = 0, Value = -1 }; }
        }
    }


    // ==========================================
    // FACE RECOGNITION SERVICE
    // ==========================================
    public class FaceRecognitionService
    {
        private readonly Dictionary<int, string> _knownFaces = new Dictionary<int, string>
        {
            { 73, "William" },    // Authorized person
            { -1, "Unknown" }     // Unknown person
        };

        public string RecognizeFace(SystemState state)
        {
            if (state.FaceCount == 0)
                return "No face detected";

            if (state.FaceCount > 1)
                return "Multiple faces detected";

            return _knownFaces.ContainsKey((int)state.Value) ? _knownFaces[(int)state.Value] : "Unknown";
        }

        public bool IsAuthorized(string person)
        {
            return person == "William";
        }
    }

    // ==========================================
    // RULE ENGINE (The Brain)
    // ==========================================
    public class LockRule
    {
        public double TriggerValue { get; set; }
        public required ILockAction Action { get; set; }
    }

    public class LockManager
    {
        private readonly IInputProvider _inputProvider;
        private readonly FaceRecognitionService _faceService;
        private readonly List<LockRule> _rules = new List<LockRule>();
        
        // CONFIGURATION FOR VISION SIMULATION
        private const double ScanThreshold = 0.8;  // Very close
        private const double PresenceThreshold = 0.3;  // Someone is there

        public LockManager(IInputProvider inputProvider, FaceRecognitionService faceService)
        {
            _inputProvider = inputProvider;
            _faceService = faceService;
        }

        public void AddRule(double value, ILockAction action) 
            => _rules.Add(new LockRule { TriggerValue = value, Action = action });

        public void Update()
        {
            SystemState state = _inputProvider.GetCurrentState();

            Console.WriteLine($"[DEBUG] Proximity: {state.Proximity:F2}, FaceCount: {state.FaceCount}, PersonName: {state.PersonName}, IsAuthorized: {state.IsAuthorized}");

            if (state.IsAuthorized && state.FaceCount > 0)
            {
                Console.WriteLine($"[SYSTEM] Authorized face detected: {state.PersonName} - UNLOCKING");
                var unlockRule = _rules.FirstOrDefault(r => r.TriggerValue == 73);
                unlockRule?.Action.Execute();
            }
            else if (state.FaceCount > 0)
            {
                Console.WriteLine($"[SYSTEM] Unauthorized face detected - LOCKING");
                var lockRule = _rules.FirstOrDefault(r => r.TriggerValue == -1);
                lockRule?.Action.Execute();
            }
        }
    }

    // ==========================================
    // MAIN ENTRY POINT
    // ==========================================
    public class Program
    {
        static void Main(string[] args)
        {
            // Use socket communication only
            IInputProvider inputSource = new SocketInputProvider(9999);
            Console.WriteLine("[SYSTEM] Using socket communication with AI recognition");
            
            FaceRecognitionService faceService = new FaceRecognitionService();
            LockManager brain = new LockManager(inputSource, faceService);
            
            // Define rules
            brain.AddRule(73, new SimulatedAction("UNLOCK", "Deadbolt Disengaged"));
            brain.AddRule(-1, new SimulatedAction("LOCK", "Deadbolt Engaged"));
            
            Console.WriteLine("Smart Lock System Online.");
            Console.WriteLine("--------------------------------------------");
            
            while (true)
            {
                brain.Update();
                Thread.Sleep(1000);
            }
        }
    }
}
