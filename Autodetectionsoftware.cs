using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Threading;

namespace SmartLockSystem
{
    // ==========================================
    // DATA MODELS
    // ==========================================
    public class SystemState
    {
        // 0.0 (Far/None) to 1.0 (Right in front of camera)
        public double Proximity { get; set; } 
        public double Value { get; set; }
        public int FaceCount { get; set; }
        public List<FaceData> FaceData { get; set; } = new List<FaceData>();
    }

    public class FaceData
    {
        public int X { get; set; }
        public int Y { get; set; }
        public int W { get; set; }
        public int H { get; set; }
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

    // ==========================================
    // SIMULATED HARDWARE ACTIONS
    // ==========================================
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
            { 10, "Stranger" }    // Unknown person
        };

        public string RecognizeFace(SystemState state)
        {
            if (state.FaceCount == 0)
                return "No face detected";

            if (state.FaceCount > 1)
                return "Multiple faces detected";

            // Simple recognition based on face position/size
            // In a real system, you'd use facial recognition algorithms
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
        private const double ScanThreshold = 0.8;  // Must be 80% close to trigger scan
        private const double PresenceThreshold = 0.3; // Anything above 30% is "someone is there"

        private double _lastProximity = -1.0;
        private double _lastValue = double.NaN;

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

            // Detection logic
            if (Math.Abs(state.Proximity - _lastProximity) > 0.05)
            {
                if (state.Proximity > PresenceThreshold && state.Proximity < ScanThreshold)
                {
                    Console.WriteLine($"[VISION] Object detected... Proximity: {state.Proximity:P0}");
                }
                else if (state.Proximity >= ScanThreshold)
                {
                    Console.WriteLine($"[VISION] Face detected. Attempting to identify...");

                    // Use face recognition service
                    string person = _faceService.RecognizeFace(state);
                    Console.WriteLine($"[RECOGNITION] {person}");

                    if (_faceService.IsAuthorized(person))
                    {
                        Console.WriteLine("[SYSTEM] Access granted");
                        // Trigger unlock action
                        var rule = _rules.FirstOrDefault(r => r.TriggerValue == 73);
                        rule?.Action.Execute();
                    }
                    else
                    {
                        Console.WriteLine("[SYSTEM] Access denied");
                    }
                }
                else if (state.Proximity <= PresenceThreshold && _lastProximity > PresenceThreshold)
                {
                    Console.WriteLine("[VISION] Area clear.");
                }
                _lastProximity = state.Proximity;
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
            string path = @"C:\Users\William\Desktop\vscode\Nya test\input.json";
            IInputProvider inputSource = new JsonInputProvider(path);
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
                Thread.Sleep(1000); // Update every second
            }
        }
    }
}