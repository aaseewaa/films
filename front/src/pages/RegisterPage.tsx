import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { register } from '@/api/auth';
import { listNewsCities } from '@/api/news';
import { AuthShell } from '@/components/auth/AuthShell';
import { AuthField, authInputClass, authSubmitButtonClass, authFormClass, authErrorClass } from '@/components/auth/AuthField';
import { Button } from '@/components/ui/Button';
import { getAuthErrorMessage } from '@/lib/authErrors';
import { useAuthStore } from '@/stores/auth';

export function RegisterPage() {
  const navigate = useNavigate();
  const { isAuthenticated, setAuth } = useAuthStore();
  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [city, setCity] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const { data: cities = [], isLoading: citiesLoading } = useQuery({
    queryKey: ['news', 'cities'],
    queryFn: listNewsCities,
  });

  useEffect(() => {
    if (isAuthenticated) navigate('/me', { replace: true });
  }, [isAuthenticated, navigate]);

  useEffect(() => {
    if (cities.length > 0 && !city) setCity(cities[0].name);
  }, [cities, city]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (password !== passwordConfirm) {
      setError('Пароли не совпадают');
      return;
    }
    if (password.length < 8) {
      setError('Пароль должен быть не короче 8 символов');
      return;
    }

    setLoading(true);
    try {
      const data = await register({
        email: email.trim(),
        password,
        display_name: displayName.trim(),
        city: city || undefined,
      });
      setAuth(data.access_token, data.user);
      navigate('/news', { replace: true });
    } catch (err) {
      setError(getAuthErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell
      title="Регистрация"
      subtitle="Создайте аккаунт — это бесплатно и не обязательно для просмотра каталога."
      showBenefits
      footer={
        <>
          <p>
            Уже есть аккаунт?{' '}
            <Link to="/auth/login" className="text-tiffany hover:underline font-medium">
              Войти
            </Link>
          </p>
          <p className="mt-4">
            <Link to="/" className="text-ink-50 hover:text-ink-300">
              Продолжить без аккаунта
            </Link>
          </p>
        </>
      }
    >
      <form onSubmit={handleSubmit} className={authFormClass}>
        {error && (
          <p className={authErrorClass}>
            {error}
          </p>
        )}

        <AuthField id="display_name" label="Имя">
          <input
            id="display_name"
            type="text"
            autoComplete="name"
            required
            minLength={2}
            maxLength={150}
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            className={authInputClass}
            placeholder="Как к вам обращаться"
          />
        </AuthField>

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
            autoComplete="new-password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className={authInputClass}
            placeholder="Не менее 8 символов"
          />
        </AuthField>

        <AuthField id="password_confirm" label="Повторите пароль">
          <input
            id="password_confirm"
            type="password"
            autoComplete="new-password"
            required
            minLength={8}
            value={passwordConfirm}
            onChange={(e) => setPasswordConfirm(e.target.value)}
            className={authInputClass}
          />
        </AuthField>

        <AuthField id="city" label="Город (для афиши в кино)">
          <select
            id="city"
            value={city}
            onChange={(e) => setCity(e.target.value)}
            className={authInputClass}
            disabled={citiesLoading}
          >
            {citiesLoading && <option value="">Загрузка…</option>}
            {cities.map((c) => (
              <option key={c.kp_city_id} value={c.name}>
                {c.name}
              </option>
            ))}
            {!citiesLoading && cities.length === 0 && (
              <option value="Москва">Москва</option>
            )}
          </select>
        </AuthField>

        <Button type="submit" className={authSubmitButtonClass} size="lg" disabled={loading}>
          {loading ? 'Создаём аккаунт…' : 'Зарегистрироваться'}
        </Button>
      </form>
    </AuthShell>
  );
}
