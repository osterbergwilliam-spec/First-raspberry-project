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
        private readonly List<LockRule> _rules = new List<LockRule>();
        
        // CONFIGURATION FOR VISION SIMULATION
        private const double ScanThreshold = 0.8;  // Must be 80% close to trigger scan
        private const double PresenceThreshold = 0.3; // Anything above 30% is "someone is there"

        private double _lastProximity = -1.0;
        private double _lastValue = double.NaN;

        public LockManager(IInputProvider inputProvider) => _inputProvider = inputProvider;

        public void AddRule(double value, ILockAction action) 
            => _rules.Add(new LockRule { TriggerValue = value, Action = action });

        public void Update()
        {
            SystemState state = _inputProvider.GetCurrentState();

            // 1. DETECT APPROACH (Closing In)
            if (Math.Abs(state.Proximity - _lastProximity) > 0.05) // Only update if change is significant
            {
                if (state.Proximity > PresenceThreshold && state.Proximity < ScanThreshold)
                {
                    Console.WriteLine($"[VISION] Object detected closing in... Proximity: {state.Proximity:P0}");
                }
                else if (state.Proximity >= ScanThreshold)
                {
                    Console.WriteLine($"[VISION] Object in range. Attempting to identify...");
                }
                else if (state.Proximity <= PresenceThreshold && _lastProximity > PresenceThreshold)
                {
                    Console.WriteLine("[VISION] Area clear.");
                }
                _lastProximity = state.Proximity;
            }

            // 2. IDENTIFICATION PHASE
            // We ONLY scan for the ID (Value) if the person is close enough
            if (state.Proximity >= ScanThreshold)
            {
                if (state.Value == _lastValue) return; 
                _lastValue = state.Value;

                Console.WriteLine($"[SCANNER] Reading ID: {state.Value}");

                var rule = _rules.FirstOrDefault(r => r.TriggerValue == state.Value);
                if (rule != null)
                {
                    rule.Action.Execute();
                }
                else
                {
                    Console.WriteLine("[SYSTEM] Access Denied: ID not recognized. Lock remains CLOSED.");
                }
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
            LockManager brain = new LockManager(inputSource);

            // Define rules
            brain.AddRule(73, new SimulatedAction("LOCKING", "Deadbolt Engaged"));
            brain.AddRule(10, new SimulatedAction("Nothing wrong", "Lock stays open"));

            Console.WriteLine("Vision Simulation Online.");
            Console.WriteLine($"Threshold for scanning: {0.8:P0}");
            Console.WriteLine("--------------------------------------------");

            while (true)
            {
                brain.Update();
                Thread.Sleep(1000); // Update every second
            }
        }
    }
}