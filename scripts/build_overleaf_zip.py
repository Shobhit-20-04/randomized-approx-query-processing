import os
import zipfile
import shutil

def build_overleaf_package():
    repo_root = os.path.abspath('D:/VIT/DSA Case Study/randomized-approx-query-processing')
    paper_dir = os.path.join(repo_root, 'paper')
    manuscript_dir = os.path.join(paper_dir, 'manuscript')
    overleaf_dir = os.path.join(paper_dir, 'overleaf')
    os.makedirs(overleaf_dir, exist_ok=True)
    
    zip_path = os.path.join(overleaf_dir, 'AdaLog_Sketch_Overleaf_Package.zip')
    
    # Files to include in the Overleaf package:
    # 1. main.tex from paper/manuscript/main.tex
    # 2. main.bbl from paper/manuscript/main.bbl
    # 3. references.bib from paper/references.bib
    # 4. algorithm.sty if present
    # 5. All figure files (.pdf and .png) from paper/
    
    files_to_pack = [
        (os.path.join(manuscript_dir, 'main.tex'), 'main.tex'),
        (os.path.join(manuscript_dir, 'main.bbl'), 'main.bbl'),
        (os.path.join(paper_dir, 'references.bib'), 'references.bib'),
    ]
    
    algo_sty = os.path.join(paper_dir, 'algorithm.sty')
    if not os.path.exists(algo_sty):
        # check if it exists in paper_local/latex/algorithm.sty
        cand = os.path.join(repo_root, 'paper_local', 'latex', 'algorithm.sty')
        if os.path.exists(cand):
            algo_sty = cand
    if os.path.exists(algo_sty):
        files_to_pack.append((algo_sty, 'algorithm.sty'))
        
    for fname in os.listdir(paper_dir):
        if fname.startswith('fig') and (fname.endswith('.pdf') or fname.endswith('.png')):
            files_to_pack.append((os.path.join(paper_dir, fname), fname))
            
    print(f"Packaging {len(files_to_pack)} files into {zip_path}...")
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for src, arcname in files_to_pack:
            if os.path.exists(src):
                z.write(src, arcname)
                print(f"  + {arcname} ({os.path.getsize(src)} bytes)")
            else:
                print(f"  ! WARNING: {src} does not exist!")

    # Also copy to artifacts directory and paper_local
    artifact_dir = r'C:\Users\Shobhit\.gemini\antigravity\brain\2e0bfc21-e3c1-4dcc-bfe2-952a1a766a47'
    artifact_zip = os.path.join(artifact_dir, 'AdaLog_Sketch_Overleaf_Package.zip')
    shutil.copy2(zip_path, artifact_zip)
    print(f"Copied to artifact dir: {artifact_zip}")
    
    paper_local_zip = os.path.join(repo_root, 'paper_local', 'AdaLog_Sketch_Overleaf_Package.zip')
    if os.path.exists(os.path.dirname(paper_local_zip)):
        shutil.copy2(zip_path, paper_local_zip)
        print(f"Copied to paper_local: {paper_local_zip}")
        
    print("Overleaf package successfully created and verified!")

if __name__ == '__main__':
    build_overleaf_package()
