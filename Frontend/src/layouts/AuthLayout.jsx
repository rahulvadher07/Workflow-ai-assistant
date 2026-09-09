import { Outlet, useLocation } from "react-router-dom";
import { Sparkles, ShieldCheck } from "lucide-react";
import authHero from "../assets/auth-hero.png";
import registerHero from "../assets/register-image.png";

export default function AuthLayout() {
  const { pathname } = useLocation();
  const isRegister = pathname === "/register";
  const heroImage = isRegister ? registerHero : authHero;

  return (
    <div className="min-h-screen bg-[#eef7f3] px-4 py-8 sm:py-10">
      <div className="mx-auto grid min-h-[calc(100vh-4rem)] w-full max-w-6xl overflow-hidden rounded-3xl border border-emerald-100/80 bg-white shadow-[0_24px_70px_rgba(15,23,42,0.12)] lg:grid-cols-[1.08fr_0.92fr]">
        <div className="relative hidden min-h-[700px] overflow-hidden bg-[#0a4037] lg:block">
          <img
            src={heroImage}
            alt="WorkFlow AI workplace"
           className="absolute inset-0 h-full w-full object-contain object-center translate-y-[50px]"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-[#052f29]/65 via-transparent to-transparent" aria-hidden="true" />
          {isRegister && (
            <div className="absolute left-8 right-8 top-28 z-10 max-w-lg text-white">
              <p className="text-[10px] font-extrabold uppercase tracking-[.18em] text-emerald-200">A smarter workplace</p>
              <h2 className="mt-3 text-3xl font-extrabold leading-tight tracking-[-.04em] sm:text-4xl">Build a better workday, from day one.</h2>
              <p className="mt-4 max-w-md text-sm leading-6 text-white/72">Bring people, processes and productivity together in one simple WorkFlow AI workspace.</p>
            </div>
          )}
          <div className="absolute left-8 top-8 flex items-center gap-3 rounded-2xl bg-white/10 px-3 py-2 backdrop-blur-md">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500 text-white shadow-lg shadow-emerald-950/20">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <div className="font-bold tracking-tight text-white">WorkFlow AI</div>
              <div className="text-[10px] uppercase tracking-[0.14em] text-white/65">Operations Hub</div>
            </div>
          </div>
          <div className="absolute bottom-7 left-8 right-8 flex items-center gap-2 rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-xs text-white/80 backdrop-blur-md">
            <ShieldCheck className="h-4 w-4 shrink-0 text-emerald-200" />
            <span>Role-based access and protected company data</span>
          </div>
        </div>
        <div className="flex items-center px-7 py-8 sm:px-10 lg:px-12">
          <div className="w-full">
            <div className="mb-8 flex items-center justify-center gap-2 lg:hidden">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-600">
                <Sparkles className="h-4 w-4 text-white" />
              </div>
              <span className="font-bold text-ink-900">WorkFlow AI</span>
            </div>
            <Outlet />
          </div>
        </div>
      </div>
    </div>
  );
}