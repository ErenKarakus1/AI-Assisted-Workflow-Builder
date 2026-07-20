import { Link, useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";

import { loginUser, registerUser, type RegisterPayload } from "../../api/auth";
import { errorMessage } from "../../lib/errors";
import { useAuth } from "./AuthProvider";

export function RegisterPage() {
  const navigate = useNavigate();
  const { signIn } = useAuth();
  const form = useForm<RegisterPayload>();
  const registerMutation = useMutation({
    mutationFn: async (values: RegisterPayload) => {
      const payload = {
        ...values,
        email: values.email.trim().toLowerCase(),
        full_name: values.full_name.trim(),
      };
      await registerUser(payload);
      return loginUser({ email: payload.email, password: payload.password });
    },
    onSuccess: async (tokens) => {
      await signIn(tokens.access_token);
      navigate("/");
    },
  });

  return (
    <main className="auth-page">
      <section className="auth-panel">
        <p className="eyebrow">Get started</p>
        <h1>Create account</h1>
        <form className="form" onSubmit={form.handleSubmit((values) => registerMutation.mutate(values))}>
          <label>
            Full name
            <input
              {...form.register("full_name", {
                required: "Full name is required",
                validate: (value) => Boolean(value.trim()) || "Full name is required",
              })}
            />
            {form.formState.errors.full_name ? (
              <span className="field-error">{form.formState.errors.full_name.message}</span>
            ) : null}
          </label>
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
            <input
              type="password"
              {...form.register("password", {
                required: "Password is required",
                minLength: {
                  value: 8,
                  message: "Password must be at least 8 characters",
                },
              })}
            />
            {form.formState.errors.password ? (
              <span className="field-error">{form.formState.errors.password.message}</span>
            ) : null}
          </label>
          {registerMutation.isError ? (
            <p className="form-error">
              {errorMessage(
                registerMutation.error,
                "Could not create that account. Check whether the email is already registered.",
              )}
            </p>
          ) : null}
          <button className="button" type="submit" disabled={registerMutation.isPending}>
            {registerMutation.isPending ? "Creating..." : "Create account"}
          </button>
        </form>
        <p className="muted">
          Already registered? <Link to="/login">Sign in</Link>
        </p>
      </section>
    </main>
  );
}
