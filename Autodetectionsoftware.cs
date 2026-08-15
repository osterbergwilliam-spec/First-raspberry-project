#nullable enable
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
        private const double ScanThreshold = 0.8;  // Very close
        private const double PresenceThreshold = 0.3;  // Someone is there

        private double _lastProximity = -1.0;

        public LockManager(IInputProvider inputProvider)
        {
            _inputProvider = inputProvider;
        }

        public void AddRule(double value, ILockAction action) 
            => _rules.Add(new LockRule { TriggerValue = value, Action = action });

        public void Update()
        {
            SystemState state = _inputProvider.GetCurrentState();
            
            Console.WriteLine($"[DEBUG] Proximity: {state.Proximity:P0}, FaceCount: {state.FaceCount}, PersonName: {state.PersonName}, IsAuthorized: {state.IsAuthorized}");
            
            if (Math.Abs(state.Proximity - _lastProximity) > 0.05)
            {
                if (state.Proximity >= 0.8 && state.FaceCount > 0)
                {
                    Console.WriteLine($"[VISION] Face detected: {state.PersonName}");
                    
                    if (state.IsAuthorized)
                    {
                        Console.WriteLine("[SYSTEM] Access granted - Unlocking");
                        var rule = _rules.FirstOrDefault(r => r.TriggerValue == 73);
                        rule?.Action.Execute();
                    }
                    else
                    {
                        Console.WriteLine("[SYSTEM] Access denied - Lock remains engaged");
                    }
                }
                else if (state.Proximity > 0.3 && state.Proximity < 0.8)
                {
                    Console.WriteLine("[VISION] Face detected but too far for recognition");
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
            LockManager brain = new LockManager(inputSource);

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