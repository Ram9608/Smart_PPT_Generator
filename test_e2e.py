from utils.llm_engine import LLMEngine
from utils.ppt_engine import PPTEngine
import os

def run_test():
    print("Starting Functional Test...")
    
    # 1. Setup
    api_key = "TEST_MOCK"
    provider = "TEST_MOCK" # modified engine supports this
    text = "This is a test of the emergency broadcast system."
    template_path = os.path.abspath("test_template.pptx")
    
    if not os.path.exists(template_path):
        print("Error: test_template.pptx not found. Run create_test_template.py first.")
        return

    # 2. Initialize Engines
    print("Initializing Engines...")
    llm = LLMEngine(provider=provider, api_key=api_key)
    ppt_gen = PPTEngine(template_path=template_path)
    
    # 3. Generate Content
    print("Generatng Slides (Mock)...")
    slides_data = llm.generate_slides(text)
    print(f"Received {len(slides_data['slides'])} slides.")
    
    # 4. Create PPT
    print("Creating Presentation...")
    final_ppt = ppt_gen.create_presentation(slides_data)
    
    # 5. Save Output
    output_file = "functional_test_output.pptx"
    with open(output_file, "wb") as f:
        f.write(final_ppt.getbuffer())
        
    if os.path.exists(output_file):
        size = os.path.getsize(output_file)
        print(f"SUCCESS: {output_file} generated ({size} bytes).")
    else:
        print("FAILURE: Output file not generated.")

if __name__ == "__main__":
    run_test()
