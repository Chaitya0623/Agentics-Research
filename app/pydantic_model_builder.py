# app.py
from __future__ import annotations

import json
from typing import Any, get_args, get_origin

import streamlit as st
from pydantic import BaseModel, Field, ValidationError, create_model

# -----------------------
# Helpers
# -----------------------

SIMPLE_TYPES = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "date": "date",
    "datetime": "datetime",
    "Any": Any,
}

LIST_TYPES = {
    "list[str]": list[str],
    "list[int]": list[int],
    "list[float]": list[float],
    "list[bool]": list[bool],
}

# Lazy imports (date/datetime are optional until needed)
def _resolve_builtin(name: str):
    if name == "date":
        import datetime
        return datetime.date
    if name == "datetime":
        import datetime
        return datetime.datetime
    raise KeyError(name)

def parse_field_type(label: str):
    """Map UI label -> Python type."""
    if label in SIMPLE_TYPES:
        t = SIMPLE_TYPES[label]
        return _resolve_builtin(t) if isinstance(t, str) else t
    if label in LIST_TYPES:
        return LIST_TYPES[label]
    if label.startswith("Literal["):
        # e.g. "Literal['A','B','C']"
        from typing import Literal
        # Very small safe parser: expect a python-ish list of comma-separated items
        items_str = label[len("Literal["):-1]
        parts = [p.strip() for p in items_str.split(",") if p.strip()]
        # Allow quotes or bare numbers/bools
        parsed = []
        for p in parts:
            if (p.startswith("'") and p.endswith("'")) or (p.startswith('"') and p.endswith('"')):
                parsed.append(p[1:-1])
            else:
                # try number/bool
                if p.lower() in ("true", "false"):
                    parsed.append(p.lower() == "true")
                else:
                    try:
                        parsed.append(int(p))
                    except ValueError:
                        try:
                            parsed.append(float(p))
                        except ValueError:
                            parsed.append(p)  # fallback as string
        return Literal[tuple(parsed)]  # type: ignore
    return Any

def type_to_str(t: Any) -> str:
    """Pretty-print a Python type into a class annotation string."""
    origin = get_origin(t)
    if origin is list:
        args = get_args(t)
        inner = type_to_str(args[0]) if args else "Any"
        return f"list[{inner}]"
    if t in (str, int, float, bool, Any):
        return t.__name__ if t is not Any else "Any"
    if t.__class__.__name__ == "NoneType":
        return "None"
    if hasattr(t, "__name__"):
        return t.__name__
    return repr(t)

def make_class_code(model_name: str, fields_spec: list[dict]) -> str:
    """Generate a Pydantic class definition string from the UI spec."""
    lines = [
        "from __future__ import annotations",
        "from pydantic import BaseModel, Field",
        "from typing import Any",
    ]
    # Check if we need date/datetime or typing extras
    needs_date = any(fs["type_label"] == "date" for fs in fields_spec)
    needs_datetime = any(fs["type_label"] == "datetime" for fs in fields_spec)
    if needs_date or needs_datetime:
        lines.append("import datetime")

    # Collect any Literal[...] labels (no extra import needed on 3.11+, but import for portability)
    if any(fs["type_label"].startswith("Literal[") for fs in fields_spec):
        lines.append("from typing import Literal")

    lines.append("")
    lines.append(f"class {model_name}(BaseModel):")
    if not fields_spec:
        lines.append("    pass")
        return "\n".join(lines)

    for fs in fields_spec:
        fname = fs["name"]
        t = parse_field_type(fs["type_label"])
        t_str = type_to_str(t)

        optional = fs["optional"]
        desc = fs["description"].strip()
        has_default = fs["use_default"]
        default_val = fs["default_value"]

        ann = t_str if not optional else f"{t_str} | None"

        # Build right-hand side
        if has_default and default_val != "":
            # Try to cast default to python value for str/int/float/bool
            dv = default_val
            if t in (int, float):
                try:
                    dv = t(default_val)
                except Exception:
                    pass
            elif t is bool:
                dv = str(default_val).strip().lower() in ("1", "true", "yes", "y", "on")
            rhs = f"Field({repr(dv)}, description={repr(desc)})" if desc else repr(dv)
        else:
            # No explicit default
            if optional:
                rhs = f"Field(default=None, description={repr(desc)})" if desc else "None"
            else:
                rhs = f"Field(..., description={repr(desc)})" if desc else "Field(...)"

        lines.append(f"    {fname}: {ann} = {rhs}")

    return "\n".join(lines)

def build_model(model_name: str, fields_spec: list[dict]):
    """Create a Pydantic model dynamically from the UI spec."""
    field_defs: dict[str, tuple[Any, Any]] = {}

    for fs in fields_spec:
        fname = fs["name"]
        t = parse_field_type(fs["type_label"])
        optional = fs["optional"]
        desc = fs["description"].strip()
        has_default = fs["use_default"]
        default_val = fs["default_value"]

        ann = t if not optional else (t | None)

        if has_default and default_val != "":
            dv = default_val
            if t in (int, float):
                try:
                    dv = t(default_val)
                except Exception:
                    pass
            elif t is bool:
                dv = str(default_val).strip().lower() in ("1", "true", "yes", "y", "on")
            field_defs[fname] = (ann, Field(dv, description=desc or None))
        else:
            if optional:
                field_defs[fname] = (ann, Field(default=None, description=desc or None))
            else:
                field_defs[fname] = (ann, Field(..., description=desc or None))

    Model = create_model(model_name, **field_defs)  # type: ignore
    return Model

# -----------------------
# UI
# -----------------------

st.set_page_config(page_title="Pydantic Model Builder", page_icon="🧱", layout="wide")
st.title("🧱 Visual Pydantic Model Builder")

with st.sidebar:
    st.markdown("### Model settings")
    model_name = st.text_input("Model name", value="MyModel")

    st.markdown("---")
    st.markdown("#### Add field")
    if "fields" not in st.session_state:
        st.session_state.fields = []

    new_name = st.text_input("Field name", key="new_field_name", placeholder="e.g., title")
    type_options = list(SIMPLE_TYPES.keys()) + list(LIST_TYPES.keys()) + ["Literal['A','B','C']"]
    new_type = st.selectbox("Field type", options=type_options, key="new_field_type", index=0)
    new_optional = st.checkbox("Optional", key="new_field_optional", value=False)
    new_use_default = st.checkbox("Set default value", key="new_use_default", value=False)
    new_default_value = st.text_input("Default (as text)", key="new_default_value", disabled=not new_use_default)
    new_description = st.text_area("Description (optional)", key="new_desc", height=80)

    if st.button("➕ Add field"):
        if not new_name.strip():
            st.warning("Please provide a field name.")
        else:
            st.session_state.fields.append(
                {
                    "name": new_name.strip(),
                    "type_label": new_type,
                    "optional": new_optional,
                    "use_default": new_use_default,
                    "default_value": new_default_value,
                    "description": new_description,
                }
            )
            st.success(f"Added field `{new_name.strip()}`")

if st.session_state.fields:
    st.markdown("### Fields")
    # editable controls per field
    to_delete = []
    for i, fs in enumerate(st.session_state.fields):
        with st.expander(f"Field #{i+1}: `{fs['name']}`", expanded=False):
            c1, c2, c3, c4 = st.columns([1.4, 1.2, 1, 0.5])
            fs["name"] = c1.text_input("Name", value=fs["name"], key=f"name_{i}")
            fs["type_label"] = c2.selectbox("Type", options=type_options, index=type_options.index(fs["type_label"]), key=f"type_{i}")
            fs["optional"] = c3.checkbox("Optional", value=fs["optional"], key=f"opt_{i}")
            fs["use_default"] = c4.checkbox("Default?", value=fs["use_default"], key=f"default_flag_{i}")

            fs["default_value"] = st.text_input("Default (as text)", value=fs["default_value"], key=f"default_val_{i}", disabled=not fs["use_default"])
            fs["description"] = st.text_area("Description", value=fs["description"], key=f"desc_{i}", height=80)

            if st.button("🗑️ Remove this field", key=f"del_{i}"):
                to_delete.append(i)
    if to_delete:
        for idx in sorted(to_delete, reverse=True):
            del st.session_state.fields[idx]
        st.rerun()
else:
    st.info("Add fields from the sidebar to begin.")

st.markdown("---")

# Build & preview
if st.session_state.fields:
    tabs = st.tabs(["▶️ Preview & Validate", "🧾 Generated Class Code", "🧩 JSON Schema"])

    with tabs[0]:
        Model = build_model(model_name, st.session_state.fields)
        st.success(f"Model `{Model.__name__}` created successfully.")

        colA, colB = st.columns(2)
        with colA:
            st.markdown("**Enter sample JSON to validate**")
            sample = st.text_area(
                "JSON input",
                value=json.dumps({f["name"]: None for f in st.session_state.fields}, indent=2),
                height=220,
            )
            if st.button("Validate JSON"):
                try:
                    data = json.loads(sample)
                    obj = Model.model_validate(data)
                    st.success("Validation succeeded.")
                    st.json(obj.model_dump())
                except (json.JSONDecodeError, ValidationError, Exception) as e:
                    st.error(f"Validation failed:\n\n{e}")

        with colB:
            st.markdown("**Create an instance with a small form**")
            form_vals = {}
            for f in st.session_state.fields:
                label = f["name"]
                t = parse_field_type(f["type_label"])
                if t is bool:
                    form_vals[label] = st.checkbox(label, value=False)
                else:
                    form_vals[label] = st.text_input(label, "")
            if st.button("Build instance from form"):
                # naive casting: try int/float/bool; leave strings otherwise
                casted = {}
                for f in st.session_state.fields:
                    name = f["name"]
                    val = form_vals[name]
                    t = parse_field_type(f["type_label"])
                    if val == "":
                        casted[name] = None
                    else:
                        if t is int:
                            try: casted[name] = int(val)
                            except: casted[name] = val
                        elif t is float:
                            try: casted[name] = float(val)
                            except: casted[name] = val
                        elif t is bool:
                            casted[name] = str(val).strip().lower() in ("1","true","yes","y","on")
                        else:
                            casted[name] = val
                try:
                    obj = Model.model_validate(casted)
                    st.success("Instance created:")
                    st.json(obj.model_dump())
                except ValidationError as e:
                    st.error(str(e))

    with tabs[1]:
        code = make_class_code(model_name, st.session_state.fields)
        st.code(code, language="python")
        st.download_button(
            "⬇️ Download as .py",
            data=code,
            file_name=f"{model_name}.py",
            mime="text/x-python",
        )

    with tabs[2]:
        Model = build_model(model_name, st.session_state.fields)
        st.json(Model.model_json_schema())