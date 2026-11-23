import { useState, type ReactNode } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { Emblem } from "@/components/Brand";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Feedback";
import { TextField } from "@/components/ui/Form";
import { homePathFor, useAuth } from "@/features/auth/AuthContext";
import { api, parseApiError } from "@/services/api";
import { passwordSchema, phoneSchema } from "@/utils/validation";

function AuthCard({ title, subtitle, children, footer }: { title: string; subtitle?: ReactNode; children: ReactNode; footer?: ReactNode }) {
  return (
    <div className="mx-auto max-w-md px-4 py-12 sm:py-16">
      <div className="border border-line bg-white px-6 py-8 shadow-soft sm:px-8">
        <div className="mb-6 flex items-center gap-3">
          <Emblem size={48} />
          <div>
            <h1 className="text-2xl">{title}</h1>
            {subtitle && <p className="text-[15px] text-ink-soft">{subtitle}</p>}
          </div>
        </div>
        {children}
      </div>
      {footer && <div className="mt-5 text-center text-[15px] text-ink-soft">{footer}</div>}
    </div>
  );
}

// --- Login -------------------------------------------------------------------------
const loginSchema = z.object({
  identifier: z.string().trim().min(3, "Enter your email address or mobile number"),
  password: z.string().min(1, "Enter your password"),
});

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [error, setError] = useState<string | null>(null);
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<z.infer<typeof loginSchema>>({ resolver: zodResolver(loginSchema) });
  const from = (location.state as { from?: string } | null)?.from;

  const onSubmit = handleSubmit(async (values) => {
    setError(null);
    try {
      const me = await login(values.identifier, values.password);
      navigate(from && !from.startsWith("/login") ? from : homePathFor(me), { replace: true });
    } catch (e) {
      setError(parseApiError(e, "Login failed.").message);
    }
  });

  return (
    <AuthCard title="Log in" subtitle="AVTBVS Membership"
      footer={<>New here? <Link to="/register" className="font-medium text-forest underline">Create an account</Link> to apply for membership.</>}>
      <form onSubmit={onSubmit} noValidate className="space-y-4">
        {error && <Alert tone="error">{error}</Alert>}
        <TextField label="Email address or mobile number" autoComplete="username" error={errors.identifier?.message} {...register("identifier")} />
        <TextField label="Password" type="password" autoComplete="current-password" error={errors.password?.message} {...register("password")} />
        <div className="flex items-center justify-between gap-3 pt-1">
          <Link to="/forgot-password" className="text-[15px] text-forest underline decoration-forest/30">Forgot password?</Link>
          <Button type="submit" loading={isSubmitting}>Log in</Button>
        </div>
      </form>
    </AuthCard>
  );
}

// --- Register ----------------------------------------------------------------------
const registerSchema = z.object({
  full_name: z.string().trim().min(2, "Enter your full name").max(150),
  email: z.string().trim().email("Enter a valid email address"),
  phone: phoneSchema,
  password: passwordSchema,
  confirm: z.string(),
}).refine((v) => v.password === v.confirm, { path: ["confirm"], message: "Passwords do not match" });

export function RegisterPage() {
  const { register: registerAccount } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const { register, handleSubmit, setError: setFieldError, formState: { errors, isSubmitting } } =
    useForm<z.infer<typeof registerSchema>>({ resolver: zodResolver(registerSchema) });

  const onSubmit = handleSubmit(async ({ confirm: _c, ...values }) => {
    setError(null);
    try {
      await registerAccount(values);
      navigate("/dashboard", { replace: true });
    } catch (e) {
      const info = parseApiError(e, "Could not create the account.");
      Object.entries(info.fieldErrors).forEach(([k, m]) => setFieldError(k as "email", { message: m }));
      setError(info.message);
    }
  });

  return (
    <AuthCard title="Create an account" subtitle="Step one towards life membership"
      footer={<>Already registered? <Link to="/login" className="font-medium text-forest underline">Log in</Link></>}>
      <p className="mb-5 text-[15px] text-ink-soft">
        An account lets you fill in the membership application. You become a member only after the committee approves it.
      </p>
      <form onSubmit={onSubmit} noValidate className="space-y-4">
        {error && <Alert tone="error">{error}</Alert>}
        <TextField label="Full name" autoComplete="name" required error={errors.full_name?.message} {...register("full_name")} />
        <TextField label="Email address" type="email" autoComplete="email" required error={errors.email?.message} {...register("email")} />
        <TextField label="Mobile number" type="tel" autoComplete="tel" inputMode="tel" required hint="We'll send a verification code by SMS"
          error={errors.phone?.message} {...register("phone")} />
        <TextField label="Password" type="password" autoComplete="new-password" required hint="At least 10 characters, with a letter and a number"
          error={errors.password?.message} {...register("password")} />
        <TextField label="Confirm password" type="password" autoComplete="new-password" required error={errors.confirm?.message} {...register("confirm")} />
        <Button type="submit" loading={isSubmitting} className="w-full">Create account</Button>
      </form>
    </AuthCard>
  );
}

// --- Forgot password ---------------------------------------------------------------
export function ForgotPasswordPage() {
  const [sent, setSent] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { register, handleSubmit, formState: { errors, isSubmitting } } =
    useForm<{ email: string }>({ resolver: zodResolver(z.object({ email: z.string().trim().email("Enter a valid email address") })) });
  const onSubmit = handleSubmit(async ({ email }) => {
    setError(null);
    try {
      const { data } = await api.post<{ message: string }>("/auth/forgot-password", { email });
      setSent(data.message);
    } catch (e) {
      setError(parseApiError(e).message);
    }
  });
  return (
    <AuthCard title="Reset your password" footer={<Link to="/login" className="text-forest underline">Back to log in</Link>}>
      {sent ? <Alert tone="success" title="Check your email">{sent} The link is valid for 30 minutes.</Alert> : (
        <form onSubmit={onSubmit} noValidate className="space-y-4">
          <p className="text-[15px] text-ink-soft">Enter the email address of your account. We'll email you a link to choose a new password.</p>
          {error && <Alert tone="error">{error}</Alert>}
          <TextField label="Email address" type="email" autoComplete="email" error={errors.email?.message} {...register("email")} />
          <Button type="submit" loading={isSubmitting} className="w-full">Send reset link</Button>
        </form>
      )}
    </AuthCard>
  );
}

// --- Reset password (also used for admin invitations) ------------------------------
const resetSchema = z.object({ password: passwordSchema, confirm: z.string() })
  .refine((v) => v.password === v.confirm, { path: ["confirm"], message: "Passwords do not match" });

export function ResetPasswordPage() {
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const invite = params.get("invite") === "1";
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<z.infer<typeof resetSchema>>({ resolver: zodResolver(resetSchema) });
  const onSubmit = handleSubmit(async ({ password }) => {
    setError(null);
    try {
      await api.post("/auth/reset-password", { token, new_password: password });
      setDone(true);
    } catch (e) {
      setError(parseApiError(e).message);
    }
  });
  return (
    <AuthCard title={invite ? "Set your password" : "Choose a new password"}>
      {!token ? <Alert tone="error">This link is incomplete. Open the link from your email again, or request a new one.</Alert>
        : done ? (
          <Alert tone="success" title="Password saved" action={<Link className="font-medium text-forest underline" to="/login">Log in</Link>}>
            You can now log in with your new password.
          </Alert>
        ) : (
          <form onSubmit={onSubmit} noValidate className="space-y-4">
            {error && <Alert tone="error">{error}</Alert>}
            <TextField label="New password" type="password" autoComplete="new-password" hint="At least 10 characters, with a letter and a number"
              error={errors.password?.message} {...register("password")} />
            <TextField label="Confirm password" type="password" autoComplete="new-password" error={errors.confirm?.message} {...register("confirm")} />
            <Button type="submit" loading={isSubmitting} className="w-full">Save password</Button>
          </form>
        )}
    </AuthCard>
  );
}

export function NotFoundPage() {
  return (
    <div className="mx-auto max-w-xl px-4 py-20 text-center">
      <h1>Page not found</h1>
      <p className="mt-2 text-ink-soft">The page you were looking for doesn't exist or has moved.</p>
      <Link to="/" className="mt-6 inline-block text-forest underline">Go to the home page</Link>
    </div>
  );
}
