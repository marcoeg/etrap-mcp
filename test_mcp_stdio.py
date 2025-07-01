#!/usr/bin/env python3
"""
Test ETRAP MCP Server via stdio transport (Standard MCP)

This script tests the ETRAP MCP server using the standard stdio transport,
similar to the Bauplan MCP client approach.
"""

import json
import subprocess
import sys
import time
import os
from typing import Dict, Any


class ETRAPMCPStdioTester:
    """Test ETRAP MCP server via stdio transport."""
    
    def __init__(self):
        self.proc = None
    
    def start_server(self):
        """Start the MCP server in stdio mode."""
        print("🚀 Starting ETRAP MCP server in stdio mode...")
        
        env = os.environ.copy()
        env['ETRAP_ORGANIZATION'] = 'lunaris'
        
        self.proc = subprocess.Popen(
            [sys.executable, '-m', 'mcp_etrap.app'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=env
        )
        
        # Give server time to start
        time.sleep(1.0)
        print("✅ Server started")
    
    def send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send a JSON-RPC request and get response."""
        if not self.proc:
            raise Exception("Server not started")
        
        request_str = json.dumps(request)
        print(f"📤 Sending: {request['method']}")
        
        self.proc.stdin.write(request_str + '\n')
        self.proc.stdin.flush()
        
        response = self.proc.stdout.readline()
        if not response:
            # Check stderr for any error messages
            stderr_output = self.proc.stderr.read()
            if stderr_output:
                print(f"❌ Server error: {stderr_output}")
            raise Exception("No response from server")
        
        return json.loads(response)
    
    def initialize_connection(self):
        """Initialize MCP connection."""
        print("\n🔗 Initializing MCP connection...")
        
        init_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "roots": {
                        "listChanged": False
                    },
                    "sampling": {}
                },
                "clientInfo": {
                    "name": "etrap-test-client",
                    "version": "1.0.0"
                }
            },
            "id": 1
        }
        
        init_response = self.send_request(init_request)
        print(f"✅ Initialize response: {init_response.get('result', {}).get('serverInfo', {}).get('name', 'Unknown')}")
        
        # Send initialized notification
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {}
        }
        self.proc.stdin.write(json.dumps(initialized_notification) + '\n')
        self.proc.stdin.flush()
        print("✅ Sent initialized notification")
    
    def list_tools(self):
        """List available tools."""
        print("\n🛠️ Listing available tools...")
        
        list_tools_request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 2
        }
        
        tools_response = self.send_request(list_tools_request)
        tools = tools_response.get('result', {}).get('tools', [])
        
        print(f"✅ Found {len(tools)} tools:")
        for tool in tools:
            print(f"   - {tool['name']}: {tool.get('description', 'No description')}")
        
        return tools
    
    def test_individual_verification(self):
        """Test individual transaction verification."""
        print("\n🧪 Test 1: Individual Transaction Verification")
        
        tx145 = {
            "id": 145,
            "account_id": "TEST800", 
            "amount": "8000.00",
            "type": "C",
            "created_at": "2025-07-01 16:54:07.289142",
            "reference": "Batch test transaction 1"
        }
        
        call_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "verify_transaction",
                "arguments": {
                    "transaction_data": tx145
                }
            },
            "id": 3
        }
        
        start_time = time.time()
        response = self.send_request(call_request)
        end_time = time.time()
        
        processing_time = int((end_time - start_time) * 1000)
        
        if 'result' in response:
            result = response['result']
            content = result.get('content', [])
            if content and len(content) > 0:
                tool_result = json.loads(content[0].get('text', '{}'))
                
                verified = tool_result.get('verified', False)
                batch_id = tool_result.get('batch_id', 'None')
                operation_type = tool_result.get('operation_type', 'None')
                
                status = "✅" if verified else "❌"
                print(f"   {status} Result: {verified}")
                print(f"   📦 Batch: {batch_id}")
                print(f"   🔧 Operation: {operation_type}")
                print(f"   ⏱️  Time: {processing_time}ms")
                
                return {"verified": verified, "batch_id": batch_id, "time": processing_time}
        
        print(f"   ❌ Unexpected response format: {response}")
        return {"verified": False, "error": "Unexpected response"}
    
    def test_time_range_verification(self):
        """Test time range verification - the critical test."""
        print("\n🧪 Test 2: Time Range Verification (Critical Test)")
        
        tx145 = {
            "id": 145,
            "account_id": "TEST800", 
            "amount": "8000.00",
            "type": "C",
            "created_at": "2025-07-01 16:54:07.289142",
            "reference": "Batch test transaction 1"
        }
        
        # Test with correct time range (should find TX 145)
        print(f"   📅 Testing correct time range (09:54:00 - 09:56:00 UTC)")
        
        call_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "verify_transaction",
                "arguments": {
                    "transaction_data": tx145,
                    "hints": {
                        "time_start": "2025-07-01T09:54:00",
                        "time_end": "2025-07-01T09:56:00"
                    }
                }
            },
            "id": 4
        }
        
        start_time = time.time()
        response = self.send_request(call_request)
        end_time = time.time()
        
        processing_time = int((end_time - start_time) * 1000)
        
        if 'result' in response:
            result = response['result']
            content = result.get('content', [])
            if content and len(content) > 0:
                tool_result = json.loads(content[0].get('text', '{}'))
                
                verified = tool_result.get('verified', False)
                batch_id = tool_result.get('batch_id', 'None')
                error = tool_result.get('error', '')
                
                status = "✅ FOUND" if verified else "❌ NOT FOUND"
                print(f"   🎯 Result: {status}")
                print(f"   📦 Batch: {batch_id}")
                print(f"   ⏱️  Time: {processing_time}ms")
                
                if error:
                    print(f"   ❌ Error: {error}")
                
                return {"verified": verified, "batch_id": batch_id, "time": processing_time}
        
        print(f"   ❌ Unexpected response format: {response}")
        return {"verified": False, "error": "Unexpected response"}
    
    def test_batch_verification(self):
        """Test batch verification with time range."""
        print("\n🧪 Test 3: Batch Verification with Time Range")
        
        transactions = [
            {
                "id": 145,
                "account_id": "TEST800", 
                "amount": "8000.00",
                "type": "C",
                "created_at": "2025-07-01 16:54:07.289142",
                "reference": "Batch test transaction 1"
            },
            {
                "id": 146,
                "account_id": "TEST801",
                "amount": "8100.50", 
                "type": "D",
                "created_at": "2025-07-01 16:54:07.289142",
                "reference": "Batch test transaction 2"
            }
        ]
        
        call_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "verify_batch",
                "arguments": {
                    "transactions": transactions,
                    "hints": {
                        "time_start": "2025-07-01T09:54:00",
                        "time_end": "2025-07-01T09:56:00"
                    }
                }
            },
            "id": 5
        }
        
        start_time = time.time()
        response = self.send_request(call_request)
        end_time = time.time()
        
        processing_time = int((end_time - start_time) * 1000)
        
        if 'result' in response:
            result = response['result']
            content = result.get('content', [])
            if content and len(content) > 0:
                tool_result = json.loads(content[0].get('text', '{}'))
                
                total = tool_result.get('total_transactions', 0)
                verified = tool_result.get('verified_count', 0)
                
                print(f"   📊 Results: {verified}/{total} verified")
                print(f"   ⏱️  Time: {processing_time}ms")
                
                # Check for TX 145 specifically
                individual_results = tool_result.get('individual_results', [])
                tx145_found = False
                
                for i, tx_result in enumerate(individual_results):
                    if i < len(transactions) and transactions[i]['id'] == 145:
                        tx145_found = tx_result.get('verified', False)
                        break
                
                print(f"   🎯 TX 145 found: {'✅' if tx145_found else '❌'}")
                
                return {"total": total, "verified": verified, "tx145_found": tx145_found}
        
        print(f"   ❌ Unexpected response format: {response}")
        return {"verified": 0, "total": 0, "tx145_found": False}
    
    def run_tests(self):
        """Run all tests."""
        print("🔬 ETRAP MCP Server Tests (stdio transport)")
        print("🎯 Testing if MCP server benefits from SDK time range fixes")
        print("=" * 70)
        
        try:
            # Start server and initialize
            self.start_server()
            self.initialize_connection()
            
            # List tools
            tools = self.list_tools()
            
            # Run tests
            individual_result = self.test_individual_verification()
            time_range_result = self.test_time_range_verification()
            batch_result = self.test_batch_verification()
            
            # Summary
            print(f"\n📊 TEST RESULTS SUMMARY")
            print("=" * 70)
            
            print(f"✅ Individual verification: {individual_result.get('verified', False)}")
            print(f"   📦 Found in batch: {individual_result.get('batch_id', 'None')}")
            
            print(f"✅ Time range verification: {time_range_result.get('verified', False)}")
            print(f"   📦 Found in batch: {time_range_result.get('batch_id', 'None')}")
            
            print(f"✅ Batch verification: {batch_result.get('verified', 0)}/{batch_result.get('total', 0)} verified")
            print(f"   🎯 TX 145 found: {'✅' if batch_result.get('tx145_found', False) else '❌'}")
            
            # Final assessment
            print(f"\n🎯 FINAL ASSESSMENT:")
            if (time_range_result.get('verified', False) and 
                batch_result.get('tx145_found', False)):
                print(f"✅ SUCCESS: MCP server benefits from SDK time range fixes!")
                print(f"✅ TX 145 time range issue RESOLVED in MCP layer!")
            else:
                print(f"❌ FAILURE: MCP server does not benefit from SDK fixes")
                print(f"❌ TX 145 time range issue NOT resolved in MCP layer")
        
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            if self.proc:
                self.proc.terminate()
                self.proc.wait()


def main():
    """Main entry point."""
    tester = ETRAPMCPStdioTester()
    tester.run_tests()


if __name__ == "__main__":
    main()