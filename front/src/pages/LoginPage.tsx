import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { login } from '@/api/auth';
import { AuthShell } from '@/components/auth/AuthShell';
import { AuthField, authInputClass } from '@/components/auth/AuthField';
import { Button } from '@/components/ui/Button';
import { getAuthErrorMessage } from '@/lib/authErrors';
import { useAuthStore } from '@/stores/auth';

export function LoginPage() {
  const navigate = useNavigate();
  const { isAuthenticated, setAuth } = useAuthStore();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isAuthenticated) navigate('/me', { replace: true });
  }, [isAuthenticated, navigate]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const data = await login({ email: email.trim(), password });
      setAuth(data.access_token, data.user);
      navigate('/me', { replace: true });
    } catch (err) {
      setError(getAuthErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell
      title="Вход"
      subtitle="Войдите, чтобы сохранять фильмы, ставить оценки и видеть афишу в своём городе."
      footer={
        <>
          <p>
            Нет аккаунта?{' '}
            <Link to="/auth/register" className="text-wine-500 hover:underline font-medium">
              Зарегистрироваться
            </Link>
          </p>
          <p className="mt-3">
            <Link to="/" className="text-ink-50 hover:text-ink-300">
              Продолжить без аккаунта
            </Link>
          </p>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        {error && (
          <p className="text-sm text-wine-500 bg-wine-500/5 border border-wine-500/20 rounded-sm px-3 py-2">
            {error}
          </p>
        )}

        <AuthField id="email" label="Email">
          <input
            id="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className={authInputClass}
            placeholder="you@example.com"
          />
        </AuthField>

        <AuthField id="password" label="Пароль">
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className={authInputClass}
            placeholder="Не менее 8 символов"
          />
        </AuthField>

        <Button type="submit" className="w-full" size="lg" disabled={loading}>
          {loading ? 'Входим…' : 'Войти'}
        </Button>
      </form>
    </AuthShell>
  );
}
