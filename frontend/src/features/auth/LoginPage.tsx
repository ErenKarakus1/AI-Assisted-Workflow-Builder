import { Link, useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";

import { loginUser, type LoginPayload } from "../../api/auth";
import { errorMessage } from "../../lib/errors";
import { useAuth } from "./AuthProvider";

export function LoginPage() {
  const navigate = useNavigate();
  const { signIn } = useAuth();
  const form = useForm<LoginPayload>();
  const loginMutation = useMutation({
    mutationFn: (values: LoginPayload) =>
      loginUser({ email: values.email.trim().toLowerCase(), password: values.password }),
    onSuccess: async (tokens) => {
      await signIn(tokens.access_token);
      navigate("/");
    },
  });

  return (
    <main className="auth-page">
      <section className="auth-panel">
        <p className="eyebrow">Welcome back</p>
        <h1>Sign in</h1>
        <form className="form" onSubmit={form.handleSubmit((values) => loginMutation.mutate(values))}>
          <label>
            Email
            <input
              type="email"
              {...form.register("email", {
                required: "Email is required",
                validate: (value) => Boolean(value.trim()) || "Email is required",
              })}
            />
            {form.formState.errors.email ? (
              <span className="field-error">{form.formState.errors.email.message}</span>
            ) : null}
          </label>
          <label>
            Password
            <input type="password" {...form.register("password", { required: "Password is required" })} />
            {form.formState.errors.password ? (
              <span className="field-error">{form.formState.errors.password.message}</span>
            ) : null}
          </label>
          {loginMutation.isError ? (
            <p className="form-error">{errorMessage(loginMutation.error, "Invalid email or password.")}</p>
          ) : null}
          <button className="button" type="submit" disabled={loginMutation.isPending}>
            {loginMutation.isPending ? "Signing in..." : "Sign in"}
          </button>
        </form>
        <p className="muted">
          New here? <Link to="/register">Create an account</Link>
        </p>
      </section>
    </main>
  );
}
