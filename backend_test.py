#!/usr/bin/env python3
"""
DailyToon Backend API Test Suite
Tests all backend endpoints for the DailyToon manga comic generator app.
"""

import requests
import json
import time
import sys
from typing import Dict, Any, Optional

# Backend URL from frontend environment
BACKEND_URL = "https://comic-journal.preview.emergentagent.com/api"

class DailyToonTester:
    def __init__(self):
        self.session = requests.Session()
        self.test_episode_id = None
        self.test_panel_id = None
        self.results = []
        
    def log_result(self, test_name: str, success: bool, details: str, response_data: Any = None):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        print(f"   Details: {details}")
        if response_data and not success:
            print(f"   Response: {response_data}")
        print()
        
        self.results.append({
            "test": test_name,
            "success": success,
            "details": details,
            "response": response_data if not success else None
        })
    
    def test_health_check(self) -> bool:
        """Test 1: Basic Health Check - GET /api/"""
        try:
            print("🔍 Testing Health Check...")
            response = self.session.get(f"{BACKEND_URL}/", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                expected_message = "DailyToon API"
                expected_status = "running"
                
                if data.get("message") == expected_message and data.get("status") == expected_status:
                    self.log_result("Health Check", True, f"API is running correctly. Response: {data}")
                    return True
                else:
                    self.log_result("Health Check", False, f"Unexpected response format. Got: {data}")
                    return False
            else:
                self.log_result("Health Check", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Health Check", False, f"Request failed: {str(e)}")
            return False
    
    def test_story_submission(self) -> bool:
        """Test 2: Story Submission & Storyboard Generation - POST /api/story/submit"""
        try:
            print("🔍 Testing Story Submission & Storyboard Generation...")
            print("   ⏳ This may take 10-30 seconds for GPT processing...")
            
            story_data = {
                "story_text": "Today I woke up feeling excited because I got accepted into my dream university! I called my best friend immediately to share the news. We decided to celebrate with ice cream. Later, my parents surprised me with a small party. It was the best day ever!",
                "character_name": "Alex",
                "character_appearance": "tall with curly brown hair, glasses, casual hoodie style"
            }
            
            response = self.session.post(
                f"{BACKEND_URL}/story/submit",
                json=story_data,
                timeout=60  # 60 seconds for GPT processing
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Validate response structure
                required_fields = ["episode_id", "title", "character_profile", "panels"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_result("Story Submission", False, f"Missing required fields: {missing_fields}", data)
                    return False
                
                # Validate panels
                panels = data.get("panels", [])
                if not isinstance(panels, list) or len(panels) < 4 or len(panels) > 6:
                    self.log_result("Story Submission", False, f"Expected 4-6 panels, got {len(panels)}", data)
                    return False
                
                # Validate panel structure
                panel_fields = ["panel_id", "order", "scene_description", "dialogue", "character_description", "background"]
                for i, panel in enumerate(panels):
                    missing_panel_fields = [field for field in panel_fields if field not in panel]
                    if missing_panel_fields:
                        self.log_result("Story Submission", False, f"Panel {i} missing fields: {missing_panel_fields}", data)
                        return False
                
                # Store for later tests
                self.test_episode_id = data["episode_id"]
                self.test_panel_id = panels[0]["panel_id"] if panels else None
                
                self.log_result("Story Submission", True, 
                    f"Successfully created episode '{data['title']}' with {len(panels)} panels. Episode ID: {self.test_episode_id}")
                return True
                
            else:
                self.log_result("Story Submission", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            self.log_result("Story Submission", False, "Request timed out after 60 seconds")
            return False
        except Exception as e:
            self.log_result("Story Submission", False, f"Request failed: {str(e)}")
            return False
    
    def test_get_all_episodes(self) -> bool:
        """Test 3: Get All Episodes - GET /api/episodes"""
        try:
            print("🔍 Testing Get All Episodes...")
            response = self.session.get(f"{BACKEND_URL}/episodes", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if not isinstance(data, list):
                    self.log_result("Get All Episodes", False, f"Expected array, got: {type(data)}", data)
                    return False
                
                # Should have at least 1 episode from previous test
                if len(data) == 0:
                    self.log_result("Get All Episodes", False, "No episodes found, expected at least 1 from story submission test")
                    return False
                
                # Validate episode structure
                episode = data[0]
                required_fields = ["episode_id", "title", "user_story_text", "created_date", "panels"]
                missing_fields = [field for field in required_fields if field not in episode]
                
                if missing_fields:
                    self.log_result("Get All Episodes", False, f"Episode missing fields: {missing_fields}", data)
                    return False
                
                self.log_result("Get All Episodes", True, f"Successfully retrieved {len(data)} episodes")
                return True
                
            else:
                self.log_result("Get All Episodes", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Get All Episodes", False, f"Request failed: {str(e)}")
            return False
    
    def test_get_specific_episode(self) -> bool:
        """Test 4: Get Specific Episode - GET /api/episodes/{episode_id}"""
        if not self.test_episode_id:
            self.log_result("Get Specific Episode", False, "No episode_id available from story submission test")
            return False
            
        try:
            print("🔍 Testing Get Specific Episode...")
            response = self.session.get(f"{BACKEND_URL}/episodes/{self.test_episode_id}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Validate response structure
                required_fields = ["episode_id", "title", "user_story_text", "created_date", "panels"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_result("Get Specific Episode", False, f"Missing required fields: {missing_fields}", data)
                    return False
                
                # Verify it's the correct episode
                if data["episode_id"] != self.test_episode_id:
                    self.log_result("Get Specific Episode", False, f"Wrong episode returned. Expected: {self.test_episode_id}, Got: {data['episode_id']}")
                    return False
                
                self.log_result("Get Specific Episode", True, f"Successfully retrieved episode: {data['title']}")
                return True
                
            elif response.status_code == 404:
                self.log_result("Get Specific Episode", False, f"Episode not found: {self.test_episode_id}")
                return False
            else:
                self.log_result("Get Specific Episode", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Get Specific Episode", False, f"Request failed: {str(e)}")
            return False
    
    def test_panel_image_generation(self) -> bool:
        """Test 5: Panel Image Generation - POST /api/panels/generate"""
        if not self.test_episode_id or not self.test_panel_id:
            self.log_result("Panel Image Generation", False, "No episode_id or panel_id available from story submission test")
            return False
            
        try:
            print("🔍 Testing Panel Image Generation...")
            print("   ⏳ This may take 30-60 seconds for OpenAI image generation...")
            
            request_data = {
                "episode_id": self.test_episode_id,
                "panel_id": self.test_panel_id
            }
            
            response = self.session.post(
                f"{BACKEND_URL}/panels/generate",
                json=request_data,
                timeout=120  # 2 minutes for image generation
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Validate response structure
                if "image_base64" not in data or "status" not in data:
                    self.log_result("Panel Image Generation", False, "Missing image_base64 or status in response", data)
                    return False
                
                # Validate base64 image
                image_base64 = data["image_base64"]
                if not isinstance(image_base64, str) or len(image_base64) < 100:
                    self.log_result("Panel Image Generation", False, f"Invalid base64 image data. Length: {len(image_base64) if isinstance(image_base64, str) else 'not string'}")
                    return False
                
                status = data["status"]
                if status not in ["generated", "cached"]:
                    self.log_result("Panel Image Generation", False, f"Unexpected status: {status}")
                    return False
                
                self.log_result("Panel Image Generation", True, 
                    f"Successfully generated image (status: {status}). Base64 length: {len(image_base64)} characters")
                return True
                
            else:
                self.log_result("Panel Image Generation", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            self.log_result("Panel Image Generation", False, "Request timed out after 120 seconds")
            return False
        except Exception as e:
            self.log_result("Panel Image Generation", False, f"Request failed: {str(e)}")
            return False
    
    def test_delete_episode(self) -> bool:
        """Test 6: Delete Episode - DELETE /api/episodes/{episode_id}"""
        if not self.test_episode_id:
            self.log_result("Delete Episode", False, "No episode_id available from story submission test")
            return False
            
        try:
            print("🔍 Testing Delete Episode...")
            response = self.session.delete(f"{BACKEND_URL}/episodes/{self.test_episode_id}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Validate response
                if "message" not in data or "episode_id" not in data:
                    self.log_result("Delete Episode", False, "Missing message or episode_id in response", data)
                    return False
                
                if data["episode_id"] != self.test_episode_id:
                    self.log_result("Delete Episode", False, f"Wrong episode_id in response. Expected: {self.test_episode_id}, Got: {data['episode_id']}")
                    return False
                
                # Verify episode is actually deleted by trying to get it
                verify_response = self.session.get(f"{BACKEND_URL}/episodes/{self.test_episode_id}", timeout=10)
                if verify_response.status_code != 404:
                    self.log_result("Delete Episode", False, f"Episode still exists after deletion. Status: {verify_response.status_code}")
                    return False
                
                self.log_result("Delete Episode", True, f"Successfully deleted episode: {self.test_episode_id}")
                return True
                
            elif response.status_code == 404:
                self.log_result("Delete Episode", False, f"Episode not found for deletion: {self.test_episode_id}")
                return False
            else:
                self.log_result("Delete Episode", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Delete Episode", False, f"Request failed: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🚀 Starting DailyToon Backend API Tests")
        print(f"📡 Backend URL: {BACKEND_URL}")
        print("=" * 60)
        
        tests = [
            ("Health Check", self.test_health_check),
            ("Story Submission", self.test_story_submission),
            ("Get All Episodes", self.test_get_all_episodes),
            ("Get Specific Episode", self.test_get_specific_episode),
            ("Panel Image Generation", self.test_panel_image_generation),
            ("Delete Episode", self.test_delete_episode)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            try:
                if test_func():
                    passed += 1
            except Exception as e:
                self.log_result(test_name, False, f"Test execution failed: {str(e)}")
        
        print("=" * 60)
        print(f"📊 TEST SUMMARY: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! DailyToon backend is working correctly.")
        else:
            print("⚠️  Some tests failed. Check the details above.")
            
        return passed, total, self.results

def main():
    """Main test execution"""
    tester = DailyToonTester()
    passed, total, results = tester.run_all_tests()
    
    # Exit with error code if tests failed
    if passed != total:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()