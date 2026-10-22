"""
Static/source-text checks that harness_decider/ reuses the existing LangChain
reasoning provider instead of duplicating it (Requirement 1.6), and that the
package is distinct from and does not modify harness/ (Requirement 1.1, 2.1).
"""
import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DECIDER_DIR = REPO_ROOT / "harness_decider"
HARNESS_DIR = REPO_ROOT / "harness"

FORBIDDEN_CHAT_CLASSES = {"ChatBedrockConverse", "ChatOpenAI", "ChatAnthropic", "ChatBedrock"}


def _iter_py_files():
    return sorted(DECIDER_DIR.glob("*.py"))


def test_decider_folder_is_not_named_harness_and_is_importable():
    assert DECIDER_DIR.name != "harness"
    assert (DECIDER_DIR / "__init__.py").exists()


def test_no_file_under_harness_decider_imports_a_chat_model_class():
    for path in _iter_py_files():
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    assert alias.name not in FORBIDDEN_CHAT_CLASSES, (
                        f"{path} imports {alias.name} directly; it must reuse "
                        "harness.lc_model.make_reasoner instead"
                    )
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name not in FORBIDDEN_CHAT_CLASSES


def test_agent_module_imports_make_reasoner_from_harness_lc_model():
    agent_src = (DECIDER_DIR / "agent.py").read_text()
    tree = ast.parse(agent_src)
    found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "harness.lc_model":
            if any(alias.name == "make_reasoner" for alias in node.names):
                found = True
    assert found, "harness_decider/agent.py must import make_reasoner from harness.lc_model"


def test_harness_folder_files_are_unchanged_set():
    expected = {"__init__.py", "agent.py", "capabilities.py", "jev_router.py", "lc_model.py"}
    actual = {p.name for p in HARNESS_DIR.glob("*.py")}
    assert actual == expected, "harness/ file set changed unexpectedly"
