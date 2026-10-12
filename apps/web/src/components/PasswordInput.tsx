import { useState } from "react";

type Props = { id: string; value: string; onChange: (v: string) => void; autoComplete: string; label?: string };

export default function PasswordInput({ id, value, onChange, autoComplete, label = "Password" }: Props) {
  const [show, setShow] = useState(false);
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <div className="pw-row">
        <input id={id} type={show ? "text" : "password"} value={value} required
          autoComplete={autoComplete} onChange={(e) => onChange(e.target.value)} />
        <button type="button" className="link" onClick={() => setShow(!show)}
          aria-label={show ? "Hide password" : "Show password"}>{show ? "Hide" : "Show"}</button>
      </div>
    </div>
  );
}
