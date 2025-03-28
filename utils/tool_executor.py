import os
import re
import subprocess
import sys

class ToolExecutor:
    """
    Class for executing tools based on tool_use directives in AI responses.
    """
    
    def __init__(self, tools_dir=None):
        """
        Initialize the ToolExecutor.
        
        Args:
            tools_dir (str, optional): The directory containing the tools. 
                                      Defaults to None (uses the 'tools' directory in the project).
        """
        if tools_dir is None:
            # Get the project root directory (parent of the utils directory)
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            self.tools_dir = os.path.join(project_root, 'tools')
        else:
            self.tools_dir = tools_dir
        
        # Dictionary of available tools and their file paths
        self.available_tools = self._discover_tools()
    
    def _discover_tools(self):
        """
        Discover available tools in the tools directory.
        
        Returns:
            dict: A dictionary of tool names and their file paths.
        """
        tools = {}
        
        if not os.path.exists(self.tools_dir):
            print(f"Tools directory not found: {self.tools_dir}")
            return tools
        
        for filename in os.listdir(self.tools_dir):
            if filename.endswith('.py'):
                tool_name = filename[:-3]  # Remove the .py extension
                tool_path = os.path.join(self.tools_dir, filename)
                tools[tool_name] = tool_path
        
        print(f"Discovered tools: {', '.join(tools.keys())}")
        return tools
    
    def extract_tool_use(self, response):
        """
        Extract tool_use directives from an AI response.
        
        Args:
            response (str): The AI response to extract tool_use directives from.
            
        Returns:
            list: A list of (tool_name, args) tuples.
        """
        tools = []
        
        print(f"Extracting tool_use from response: {response[:100]}...")
        
        # First, try to extract from JSON
        try:
            import json
            json_response = json.loads(response)
            print(f"Successfully parsed JSON: {json_response.keys()}")
            if 'tool_use' in json_response:
                tool_use = json_response['tool_use']
                print(f"Found tool_use in JSON: {tool_use}")
                self._extract_tool_from_directive(tool_use, tools)
            else:
                print(f"No tool_use field in JSON")
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            print(f"Error parsing JSON: {str(e)}")
        
        # If no tools found in JSON, try regex
        if not tools:
            print("Trying regex extraction")
            # Look for "tool_use: [tool_name]" pattern with more flexible matching
            pattern = r'tool_use\s*:?\s*\[([^\]]+)\]'  # Matches tool_use: [dance] or tool_use [dance]
            
            matches = list(re.finditer(pattern, response, re.IGNORECASE))
            print(f"Found {len(matches)} regex matches")
            
            for match in matches:
                tool_name = match.group(1).lower()
                # Extract arguments if any (everything after the tool name until the end of the line)
                args_match = re.search(rf'\[{re.escape(match.group(1))}\](.*?)($|\n)', response[match.end():])
                args = args_match.group(1).strip() if args_match else ""
                tools.append((tool_name, args))
                print(f"Extracted tool from regex: {tool_name} with args: {args}")
        
        return tools
    
    def _extract_tool_from_directive(self, tool_use, tools):
        """
        Extract tool name and arguments from a tool_use directive.
        
        Args:
            tool_use (str): The tool_use directive.
            tools (list): The list to append (tool_name, args) tuples to.
        """
        # Extract tool name from [tool_name]
        match = re.search(r'\[([^\]]+)\]', tool_use)
        if match:
            tool_name = match.group(1).lower()
            # Extract arguments if any
            args = tool_use.replace(f'[{match.group(1)}]', '').strip()
            tools.append((tool_name, args))
            print(f"Extracted tool: {tool_name} with args: {args}")
        else:
            print(f"No tool name match in tool_use: {tool_use}")
        
        print(f"Extracted tools: {tools}")
        return tools
    
    def execute_tools(self, response):
        """
        Execute tools based on tool_use directives in an AI response.
        
        Args:
            response (str): The AI response to extract tool_use directives from.
            
        Returns:
            dict: A dictionary with tool results and a formatted message for the user.
        """
        print(f"\n\n==== EXECUTING TOOLS ====")
        print(f"Response: {response[:100]}...")
        
        results = []
        tools = self.extract_tool_use(response)
        formatted_results = []
        
        # Prevent duplicate tool executions by using a set to track executed tools
        executed_tools = set()
        
        print(f"Found {len(tools)} tools to execute")
        
        for tool_name, args in tools:
            # Skip if this tool has already been executed
            if tool_name in executed_tools:
                print(f"Skipping duplicate execution of tool: {tool_name}")
                continue
                
            # Add to executed tools set
            executed_tools.add(tool_name)
            if tool_name in self.available_tools:
                tool_path = self.available_tools[tool_name]
                try:
                    # Execute the tool
                    cmd = [sys.executable, tool_path]
                    if args:
                        cmd.extend(args.split())
                    
                    print(f"Executing tool: {tool_name} with args: {args}")
                    print(f"Command: {' '.join(cmd)}")
                    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    stdout, stderr = process.communicate()
                    
                    if process.returncode == 0:
                        output = stdout.strip()
                        print(f"Tool {tool_name} executed successfully: {output}")
                        formatted_results.append(f"✅ Tool [{tool_name}] executed successfully: {output}")
                    else:
                        output = f"Error: {stderr.strip()}"
                        print(f"Tool {tool_name} failed: {output}")
                        formatted_results.append(f"❌ Tool [{tool_name}] failed: {output}")
                    
                    results.append((tool_name, output))
                except Exception as e:
                    error = f"Error executing tool {tool_name}: {str(e)}"
                    print(error)
                    results.append((tool_name, error))
                    formatted_results.append(f"❌ Tool [{tool_name}] error: {str(e)}")
            else:
                error = f"Tool not found: {tool_name}"
                print(error)
                results.append((tool_name, error))
                formatted_results.append(f"❌ Tool [{tool_name}] not found")
        
        # Create a formatted message for the user
        user_message = ""
        if formatted_results:
            user_message = "\n\n" + "\n".join(formatted_results)
            print(f"Formatted message for user: {user_message}")
        else:
            print("No tools executed, no message for user")
        
        result = {
            "results": results,
            "message": user_message
        }
        
        print(f"==== TOOL EXECUTION COMPLETE ====\n\n")
        return result