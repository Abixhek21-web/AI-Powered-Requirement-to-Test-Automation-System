from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
import tempfile
from src.ingestion import load_documents, split_documents
from src.retriever import HybridRetriever
from src.generator import TestGenerator
from src.config import config
import traceback

def _friendly_error(e: Exception) -> str:
    """Returns a user-friendly error message, detecting common API issues."""
    msg = str(e)
    if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
        return (
            "Gemini API quota exceeded. Your current API key has hit its rate limit. "
            "Please wait a minute and try again, or update your GEMINI_API_KEY in the .env file with a key that has available quota."
        )
    if "401" in msg or "API_KEY_INVALID" in msg or "INVALID_ARGUMENT" in msg and "key" in msg.lower():
        return "Invalid Gemini API key. Please check your GEMINI_API_KEY in the .env file."
    return msg

app = Flask(__name__)
CORS(app) # Enable CORS for all routes

# Global memory for the retriever
global_retriever = None

@app.route('/')
def index():
    return render_template('index.html', default_model=config.default_model)

@app.route('/api/load', methods=['POST'])
def load_docs():
    global global_retriever
    data = request.get_json()
    data_dir = data.get('dataDir', 'data/input')
    
    if not os.path.exists(data_dir) or not os.path.isdir(data_dir):
        return jsonify({"success": False, "error": f"Directory not found: {data_dir}"}), 400
        
    try:
        docs = load_documents(data_dir)
        if not docs:
            return jsonify({"success": False, "error": f"No valid documents found in {data_dir}."}), 400
            
        chunks = split_documents(docs)
        global_retriever = HybridRetriever(chunks)
        
        return jsonify({
            "success": True, 
            "message": f"Loaded {len(docs)} documents. Created {len(chunks)} chunks for retrieval.",
            "docCount": len(docs),
            "chunkCount": len(chunks)
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": _friendly_error(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload_docs():
    global global_retriever
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "error": "No selected file"}), 400
        
    try:
        # Create a temporary directory for the uploaded file
        upload_dir = os.path.join(tempfile.gettempdir(), 'ai_test_gen_uploads')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save the file
        file_path = os.path.join(upload_dir, file.filename)
        file.save(file_path)
        
        # Load and process the document
        docs = load_documents(file_path)
        if not docs:
            return jsonify({"success": False, "error": "Could not parse the uploaded document."}), 400
            
        chunks = split_documents(docs)
        global_retriever = HybridRetriever(chunks)
        
        return jsonify({
            "success": True, 
            "message": f"Successfully uploaded and processed {file.filename}.",
            "docCount": len(docs),
            "chunkCount": len(chunks)
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": _friendly_error(e)}), 500

@app.route('/api/generate', methods=['POST'])
def generate_tests():
    global global_retriever
    if global_retriever is None:
        return jsonify({"success": False, "error": "Retriever not initialized. Please load documents first."}), 400
        
    data = request.get_json()
    query = data.get('query')
    framework = data.get('framework', 'Selenium Python')
    ui_context = data.get('uiContext', '')
    
    if not query:
        return jsonify({"success": False, "error": "Query is required."}), 400
        
    try:
        generator = TestGenerator(global_retriever)
        
        # Generate Test Cases
        test_cases_md = generator.generate_test_cases(query)
        
        # Generate Automation Script
        script_stub = generator.generate_automation_script(test_cases_md, framework, ui_context)
        
        # Clean up the output markdown code block format (if present)
        clean_script = script_stub
        for prefix in ['```python', '```javascript', '```typescript', '```java', '```js', '```ts', '```']:
            if clean_script.startswith(prefix):
                clean_script = clean_script[len(prefix):].strip()
        if clean_script.endswith('```'):
            clean_script = clean_script[:-3].strip()
            
        ext = ".py"
        lang = "python"
        if "js" in framework.lower() or "javascript" in framework.lower(): 
            ext = ".js"
            lang = "javascript"
        elif "ts" in framework.lower() or "typescript" in framework.lower(): 
            ext = ".ts"
            lang = "typescript"
        elif "java" in framework.lower() and "javascript" not in framework.lower(): 
            ext = ".java"
            lang = "java"
            
        # Structured Analysis for Tabs
        analysis = generator.generate_structured_analysis(query)
        
        return jsonify({
            "success": True,
            "test_cases": test_cases_md,
            "script": clean_script,
            "extension": ext,
            "language": lang,
            "traceability": analysis.get('traceability', []),
            "edges": analysis.get('edges', []),
            "risks": analysis.get('risks', [])
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/generate_multimodal', methods=['POST'])
def generate_multimodal():
    global global_retriever
    if global_retriever is None:
        return jsonify({"success": False, "error": "Retriever not initialized. Please load documents first."}), 400
        
    query = request.form.get('query')
    framework = request.form.get('framework', 'Selenium Python')
    image_file = request.files.get('image')
    
    if not query or not image_file:
        return jsonify({"success": False, "error": "Query and image are required."}), 400
        
    try:
        # Save image temporarily
        fd, temp_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        image_file.save(temp_path)
        
        generator = TestGenerator(global_retriever)
        script = generator.generate_multimodal_tests(temp_path, query, framework)
        
        # Clean up
        os.remove(temp_path)
        
        # Clean up the output markdown code block format (if present)
        clean_script = script
        for prefix in ['```python', '```javascript', '```typescript', '```java', '```js', '```ts', '```']:
            if clean_script.startswith(prefix):
                clean_script = clean_script[len(prefix):].strip()
        if clean_script.endswith('```'):
            clean_script = clean_script[:-3].strip()
            
        ext = ".py"
        lang = "python"
        if "js" in framework.lower() or "javascript" in framework.lower(): 
            ext = ".js"
            lang = "javascript"
        elif "ts" in framework.lower() or "typescript" in framework.lower(): 
            ext = ".ts"
            lang = "typescript"
        elif "java" in framework.lower() and "javascript" not in framework.lower(): 
            ext = ".java"
            lang = "java"
            
        return jsonify({
            "success": True,
            "script": clean_script,
            "extension": ext,
            "language": lang
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/heal_script', methods=['POST'])
def heal_script():
    global global_retriever
    data = request.get_json()
    broken_script = data.get('broken_script')
    error_log = data.get('error_log')
    new_dom = data.get('new_dom')
    
    if not broken_script or not error_log or not new_dom:
        return jsonify({"success": False, "error": "Missing required fields."}), 400
        
    try:
        generator = TestGenerator(global_retriever)
        fixed_script = generator.heal_script(broken_script, error_log, new_dom)
        clean_script = fixed_script
        for prefix in ['```python', '```javascript', '```typescript', '```java', '```js', '```ts', '```']:
            if clean_script.startswith(prefix):
                clean_script = clean_script[len(prefix):].strip()
        if clean_script.endswith('```'):
            clean_script = clean_script[:-3].strip()
            
        return jsonify({"success": True, "script": clean_script})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/generate_data', methods=['POST'])
def generate_data():
    global global_retriever
    data = request.get_json()
    business_rules = data.get('business_rules')
    
    if not business_rules:
        return jsonify({"success": False, "error": "Business rules are required."}), 400
        
    try:
        generator = TestGenerator(global_retriever)
        synthetic_data = generator.generate_synthetic_data(business_rules)
        clean_data = synthetic_data
        if clean_data.startswith('```json'):
            clean_data = clean_data[7:].strip()
        elif clean_data.startswith('```'):
            clean_data = clean_data[3:].strip()
        if clean_data.endswith('```'):
            clean_data = clean_data[:-3].strip()
            
        return jsonify({"success": True, "data": clean_data})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/chaos_api', methods=['POST'])
def chaos_api():
    global global_retriever
    data = request.get_json()
    api_spec = data.get('api_spec')
    
    if not api_spec:
        return jsonify({"success": False, "error": "API spec is required."}), 400
        
    try:
        generator = TestGenerator(global_retriever)
        chaos_script = generator.generate_api_chaos_script(api_spec)
        clean_script = chaos_script
        if clean_script.startswith('```python'):
            clean_script = clean_script[9:].strip()
        elif clean_script.startswith('```'):
            clean_script = clean_script[3:].strip()
        if clean_script.endswith('```'):
            clean_script = clean_script[:-3].strip()
            
        return jsonify({"success": True, "script": clean_script})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/evaluate', methods=['POST'])
def evaluate_output():
    global global_retriever
    if global_retriever is None:
        return jsonify({"success": False, "error": "Retriever not initialized."}), 400
        
    data = request.get_json()
    query = data.get('query')
    test_cases = data.get('test_cases')
    script = data.get('script')
    
    if not query or not test_cases or not script:
        return jsonify({"success": False, "error": "Missing input for evaluation."}), 400
        
    try:
        from src.evaluator import Evaluator
        from src.feedback_handler import FeedbackHandler
        evaluator = Evaluator()
        feedback = FeedbackHandler()
        
        syntax_valid = evaluator.validate_python_syntax(script)
        pom_results = evaluator.check_pom_compliance(script)
        resource_results = evaluator.check_resource_leaks(script)
        rtm_results = evaluator.verify_rtm_mapping(test_cases, script)
        ai_eval = evaluator.ai_judge_evaluation(query, query, test_cases)
        
        judge_metrics = [ai_eval.get('groundedness', 0), ai_eval.get('coverage', 0), ai_eval.get('clarity', 0)]
        judge_avg = sum(judge_metrics) / len(judge_metrics) if judge_metrics else 0
        judge_score_100 = (judge_avg / 5) * 100
        
        overall_score = (syntax_valid * 10) + (pom_results['score'] * 0.2) + (rtm_results['rtm_coverage_score'] * 0.2) + (judge_score_100 * 0.5)
        
        scores = {
            "syntax": syntax_valid,
            "pom": pom_results['compliant'],
            "resources": resource_results['safe'],
            "rtm": rtm_results['rtm_coverage_score'],
            "groundedness": ai_eval.get('groundedness', 0),
            "coverage": ai_eval.get('coverage', 0),
            "clarity": ai_eval.get('clarity', 0),
            "overall": round(overall_score, 1)
        }

        report = f"""## AI Test Generation Audit Report

### 1. Architectural Metrics
| Metric | Status | Details |
| :--- | :--- | :--- |
| **Python Syntax** | {"✅ Pass" if syntax_valid else "❌ Fail"} | {"Valid Python." if syntax_valid else "Syntax errors."} |
| **POM Compliance** | {"✅ Pass" if pom_results['compliant'] else "⚠️ Partial"} | Score: {pom_results['score']}% |
| **Resource Safety** | {"✅ Safe" if resource_results['safe'] else "❌ Leak Risk"} | {resource_results['details']} |
| **RTM Traceability** | {rtm_results['rtm_coverage_score']}% | Mapped IDs: {", ".join(rtm_results['mapped_ids'][:5])} |

### 2. AI Qualitative Review
- **Groundedness**: {ai_eval.get('groundedness', 0)}/5
- **Coverage**: {ai_eval.get('coverage', 0)}/5
- **Clarity**: {ai_eval.get('clarity', 0)}/5

**Summary**: {ai_eval.get('summary', 'Evaluation complete.')}
"""
        if not syntax_valid or rtm_results['rtm_coverage_score'] < 50:
            feedback.log_failure("GENERATION_QUALITY", f"Low score: {overall_score}", f"Query: {query}")

        return jsonify({"success": True, "report": report, "scores": scores})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/copilot', methods=['POST'])
def copilot_chat():
    global global_retriever
    data = request.get_json()
    query = data.get('query')
    previous_test_cases = data.get('test_cases', '')
    
    if not query:
        return jsonify({"success": False, "error": "Query is required."}), 400
        
    if global_retriever is None:
        return jsonify({
            "success": False, 
            "error": "Quality context is missing. Please upload your SRS document or click 'Load' on the homepage first so I can assist you with your specific requirements."
        }), 400
        
    try:
        generator = TestGenerator(global_retriever)
        if previous_test_cases:
            # Refinement mode
            response = generator.refine_test_cases(previous_test_cases, query)
        else:
            # Exploratory mode (general QA advice or first-gen)
            response = generator.generate_test_cases(query)
            
        return jsonify({
            "success": True, 
            "response": response
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/save-script', methods=['POST'])
def save_script():
    data = request.json
    code = data.get('code')
    filename = data.get('filename', 'generated_test.py')
    try:
        # Save to the root or a 'generated' folder
        save_path = os.path.join(os.getcwd(), filename)
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(code)
        return jsonify({"success": True, "message": f"Saved to {filename}"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/validate-script', methods=['POST'])
def validate_script():
    import ast
    data = request.json
    code = data.get('code')
    try:
        ast.parse(code)
        return jsonify({"success": True})
    except SyntaxError as e:
        return jsonify({"success": False, "error": f"Line {e.lineno}: {e.msg}"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
