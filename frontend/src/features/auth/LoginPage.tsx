import { useState, type FormEvent } from "react";
import { Navigate } from "react-router-dom";

import { Button } from "../../components/Button/Button";
import { useAuth } from "../../auth/AuthContext";
import forms from "../../styles/forms.module.css";
import styles from "./LoginPage.module.css";

export default function LoginPage() {
  const { user, login } = useAuth();
  const [email, setEmail] = useState("admin@retail.os");
  const [password, setPassword] = useState("admin123");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (user) return <Navigate to="/" replace />;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await login(email, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка входа");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className={styles.overlay}>
      <form className={styles.card} onSubmit={handleSubmit}>
        <div className={styles.brand}>RETAILDESIGN&nbsp;OS</div>
        <div className={styles.subtitle}>Вход в систему трекинга оборудования</div>

        <div className={forms.row} style={{ marginTop: 20 }}>
          <label className={forms.label} htmlFor="login-email">
            Email
          </label>
          <input
            id="login-email"
            type="email"
            className={forms.input}
            value={email}
            autoComplete="username"
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>
        <div className={forms.row} style={{ marginBottom: 8 }}>
          <label className={forms.label} htmlFor="login-pass">
            Пароль
          </label>
          <input
            id="login-pass"
            type="password"
            className={forms.input}
            value={password}
            autoComplete="current-password"
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        <div className={forms.error}>{error}</div>
        <Button
          type="submit"
          variant="primary"
          disabled={submitting}
          style={{ width: "100%", padding: 10 }}
        >
          {submitting ? "Входим…" : "Войти →"}
        </Button>

        <div className={styles.demoHint}>
          Демо-доступы (пароль = роль+123):
          <br />
          admin@retail.os · manager@retail.os · brand@retail.os
          <br />
          retailer@retail.os · viewer@retail.os
        </div>
      </form>
    </div>
  );
}
