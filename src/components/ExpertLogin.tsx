import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { User, Lock, Eye, EyeOff, LogIn } from 'lucide-react';
import { useNavigate } from 'react-router';
import { useToast } from '@/hooks/use-toast';
import { env } from '@/lib/env';
import { useSiteSettings } from '@/contexts/SiteSettingsContext';
import { consumeReturnTo } from '@/lib/authContinuity';
import { useI18n } from '@/i18n';

const ExpertLogin = ({ triggerClassName = "" }: { triggerClassName?: string }) => {
  const settings = useSiteSettings();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();
  const { toast } = useToast();
  const crmPrimaryRoles = new Set(['crm_manager', 'business_expert']);
  const { t } = useI18n();

  // Logout function
  const handleLogout = () => {
    localStorage.removeItem('expert_user');
    localStorage.removeItem('expert_token');
    navigate('/');
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await fetch(`${env.API_URL}/api/expert/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username,
          password
        })
      });

      const data = await response.json();

      if (response.ok && data.success) {
        // Store expert info and token in localStorage
        localStorage.setItem('expert_user', JSON.stringify(data.expert));
        localStorage.setItem('expert_token', data.tokens.access_token);
        localStorage.setItem('expert_refresh_token', data.tokens.refresh_token);
        
        toast({
          title: "ورود موفق",
          description: `به پنل ${data.expert.full_name} خوش آمدید`
        });
        
        const roleFallback = data.expert.role === 'admin'
          ? '/admin'
          : crmPrimaryRoles.has(data.expert.role) ? '/crm' : '/expert';
        navigate(consumeReturnTo(roleFallback), { replace: true });
      } else {
        setError(data.error || 'نام کاربری یا رمز عبور اشتباه است');
      }
    } catch (error) {
      console.error('Login error:', error);
      setError('خطا در ورود. لطفاً دوباره تلاش کنید');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="outline" className={`text-sm font-medium ${triggerClassName}`}>
          <User className="w-4 h-4 ml-2" />
          {t("command.staffLogin")}
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="text-center text-xl font-bold">
            ورود
          </DialogTitle>
        </DialogHeader>
        
        <form onSubmit={handleLogin} className="space-y-4">
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          
          <div className="space-y-2">
            <Label htmlFor="username">نام کاربری</Label>
            <div className="relative">
              <User className="absolute right-3 top-3 w-4 h-4 text-gray-400" />
              <Input
                id="username"
                type="text"
                placeholder="نام کاربری خود را وارد کنید"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="pr-10"
                required
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="password">رمز عبور</Label>
            <div className="relative">
              <Lock className="absolute right-3 top-3 w-4 h-4 text-gray-400" />
              <Input
                id="password"
                type={showPassword ? "text" : "password"}
                placeholder="رمز عبور خود را وارد کنید"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="pr-10 pl-10"
                required
              />
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="absolute left-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </Button>
            </div>
          </div>

          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin ml-2" />
                در حال ورود...
              </>
            ) : (
              <>
                <LogIn className="w-4 h-4 ml-2" />
                ورود
              </>
            )}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default ExpertLogin;
