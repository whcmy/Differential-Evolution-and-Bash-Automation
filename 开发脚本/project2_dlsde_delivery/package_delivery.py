"""Package the verified reproduction, excluding machine-specific dependencies."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parent


def main():
    required = {"results": 600, "results_ablation": 3600, "results_reference": 600}
    for name, expected in required.items():
        manifest = json.loads((ROOT / name / "manifest.json").read_text(encoding="utf-8"))
        assert "completed_utc" in manifest
        assert manifest["result_count"] == expected
        assert len(list((ROOT / name).glob("*/*.json"))) == expected
    audit = json.loads((ROOT / "output/verification.json").read_text(encoding="utf-8"))
    reference_audit = json.loads((ROOT / "output_reference/verification.json").read_text(encoding="utf-8"))
    assert audit["valid"] and audit["course_full"] and audit["checked_records"] == 4200
    assert reference_audit["valid"] and reference_audit["checked_records"] == 600
    files = [p for p in ROOT.iterdir() if p.is_file() and p.suffix in (".py", ".ps1", ".md", ".txt")]
    for folder in ("results", "results_ablation", "results_reference", "output", "output_reference"):
        files.extend(p for p in (ROOT / folder).rglob("*") if p.is_file())
    files.extend(p for p in (ROOT / "reference").iterdir()
                 if p.is_file() and p.suffix in (".md", ".json", ".csv", ".cpp", ".zip"))
    source_files = sorted(set(files))
    package_manifest = dict(records=4800, course_records=4200, reference_records=600,
                            excluded=[".vendor", ".audit_vendor", "tmp", ".mplconfig", "__pycache__"],
                            files={str(p.relative_to(ROOT)).replace("\\", "/"):hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in source_files})
    manifest_file = ROOT / "delivery_manifest.json"
    manifest_file.write_text(json.dumps(package_manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    target = ROOT / "DLS-DE_project2_delivery.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in source_files + [manifest_file]:
            z.write(p, "project2/" + str(p.relative_to(ROOT)).replace("\\", "/"))
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None
        assert all("/.vendor/" not in n and "/tmp/" not in n for n in z.namelist())
    checksum = hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix(".zip.sha256").write_text(checksum + "  " + target.name + "\n", encoding="ascii")
    print(json.dumps(dict(path=str(target), files=len(source_files) + 1, bytes=target.stat().st_size, sha256=checksum), indent=2))


if __name__ == "__main__":
    main()
