import React from 'react';
import { Building2, Zap, Shield, TrendingUp } from 'lucide-react';
import { Button } from '../components/ui/button';

// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH

export default function LoginPage() {
  const handleGoogleLogin = () => {
    const redirectUrl = window.location.origin + '/dashboard';
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  return (
    <div className="min-h-screen flex relative overflow-hidden" data-testid="login-page">
      {/* Animated background */}
      <div className="absolute inset-0 bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
        {/* Ambient lights */}
        <div className="absolute top-0 left-1/4 w-[600px] h-[600px] bg-cyan-500/10 rounded-full blur-[120px] animate-pulse"></div>
        <div className="absolute bottom-0 right-1/4 w-[600px] h-[600px] bg-blue-500/10 rounded-full blur-[120px] animate-pulse" style={{ animationDelay: '1s' }}></div>
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-purple-500/5 rounded-full blur-[150px]"></div>
        
        {/* Grid pattern */}
        <div className="absolute inset-0 opacity-[0.02]" style={{
          backgroundImage: `linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)`,
          backgroundSize: '60px 60px'
        }}></div>
      </div>

      {/* Left Panel - Branding */}
      <div className="hidden lg:flex lg:w-1/2 relative">
        <div className="relative z-10 flex flex-col justify-center p-16 xl:p-24">
          {/* Logo */}
          <div className="flex items-center gap-4 mb-16 animate-fade-in">
            <div className="relative">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center shadow-2xl shadow-cyan-500/30">
                <Building2 className="w-8 h-8 text-white" />
              </div>
              <div className="absolute -top-1 -right-1 w-4 h-4 bg-emerald-400 rounded-full border-2 border-slate-900 animate-pulse"></div>
            </div>
            <div>
              <h1 className="text-3xl font-bold text-white tracking-tight">PropTech</h1>
              <p className="text-cyan-400 font-medium">Decision Copilot</p>
            </div>
          </div>

          {/* Hero Text */}
          <div className="space-y-6 animate-fade-in stagger-2">
            <h2 className="text-5xl xl:text-6xl font-bold text-white leading-tight">
              AI-Powered
              <br />
              <span className="gradient-text">Property Intelligence</span>
            </h2>
            <p className="text-xl text-slate-400 max-w-lg leading-relaxed">
              Transform your real estate portfolio with intelligent analytics, predictive insights, and strategic decision support.
            </p>
          </div>

          {/* Features */}
          <div className="mt-16 grid grid-cols-1 gap-6 animate-fade-in stagger-3">
            {[
              { icon: Zap, title: 'Real-time Analytics', desc: 'Track occupancy and energy in real-time' },
              { icon: TrendingUp, title: 'Predictive Insights', desc: '7-day forecasting with AI models' },
              { icon: Shield, title: 'Risk Assessment', desc: 'Identify optimization opportunities' },
            ].map((feature, idx) => (
              <div 
                key={idx} 
                className="flex items-start gap-4 p-4 rounded-xl bg-white/[0.02] border border-white/5 backdrop-blur-sm hover:bg-white/[0.04] transition-colors group"
              >
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-cyan-500/10 to-blue-500/10 flex items-center justify-center border border-cyan-500/20 group-hover:border-cyan-500/40 transition-colors">
                  <feature.icon className="w-6 h-6 text-cyan-400" />
                </div>
                <div>
                  <h3 className="font-semibold text-white">{feature.title}</h3>
                  <p className="text-sm text-slate-500">{feature.desc}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Stats */}
          <div className="mt-16 flex items-center gap-12 animate-fade-in stagger-4">
            <div>
              <p className="text-4xl font-bold gradient-text">3M+</p>
              <p className="text-sm text-slate-500">Sq. ft. managed</p>
            </div>
            <div className="w-px h-12 bg-white/10"></div>
            <div>
              <p className="text-4xl font-bold gradient-text">₹15Cr</p>
              <p className="text-sm text-slate-500">Savings delivered</p>
            </div>
            <div className="w-px h-12 bg-white/10"></div>
            <div>
              <p className="text-4xl font-bold gradient-text">98%</p>
              <p className="text-sm text-slate-500">Accuracy rate</p>
            </div>
          </div>
        </div>
      </div>

      {/* Right Panel - Login Form */}
      <div className="flex-1 flex items-center justify-center p-8 relative z-10">
        <div className="w-full max-w-md space-y-8 animate-slide-up">
          {/* Mobile Logo */}
          <div className="lg:hidden flex items-center justify-center gap-3 mb-12">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/30">
              <Building2 className="w-7 h-7 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">PropTech</h1>
              <p className="text-sm text-cyan-400 font-medium">Decision Copilot</p>
            </div>
          </div>

          {/* Login Card */}
          <div className="glass rounded-3xl p-10 border border-white/10 shadow-2xl shadow-black/50">
            <div className="text-center space-y-3 mb-10">
              <h3 className="text-3xl font-bold text-white tracking-tight">Welcome Back</h3>
              <p className="text-slate-400">
                Sign in to access your property dashboard
              </p>
            </div>

            {/* Google Login Button */}
            <Button
              onClick={handleGoogleLogin}
              className="w-full h-14 bg-white hover:bg-slate-100 text-slate-900 rounded-xl font-semibold flex items-center justify-center gap-3 transition-all hover:shadow-xl hover:shadow-white/10 hover:scale-[1.02] active:scale-[0.98]"
              data-testid="google-login-btn"
            >
              <svg className="w-6 h-6" viewBox="0 0 24 24">
                <path
                  fill="#4285F4"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                />
                <path
                  fill="#34A853"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="#FBBC05"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                />
                <path
                  fill="#EA4335"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                />
              </svg>
              Continue with Google
            </Button>

            <div className="relative my-8">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-white/10"></div>
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="px-4 text-slate-500 bg-slate-900/50 backdrop-blur-sm rounded-full">
                  Enterprise SSO
                </span>
              </div>
            </div>

            <p className="text-center text-xs text-slate-500">
              By signing in, you agree to our{' '}
              <span className="text-cyan-400 hover:underline cursor-pointer">Terms of Service</span>
              {' '}and{' '}
              <span className="text-cyan-400 hover:underline cursor-pointer">Privacy Policy</span>
            </p>
          </div>

          {/* Footer */}
          <p className="text-center text-xs text-slate-600">
            © 2026 PropTech Decision Copilot. All rights reserved.
          </p>
        </div>
      </div>
    </div>
  );
}
