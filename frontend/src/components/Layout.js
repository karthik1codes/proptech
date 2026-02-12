import React, { useContext } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import { 
  Building2, LayoutDashboard, Target, BarChart3, 
  LogOut, Sun, Moon, Menu, X, User
} from 'lucide-react';
import { Button } from './ui/button';
import { Avatar, AvatarFallback, AvatarImage } from './ui/avatar';
import { 
  DropdownMenu, 
  DropdownMenuContent, 
  DropdownMenuItem, 
  DropdownMenuSeparator,
  DropdownMenuTrigger 
} from './ui/dropdown-menu';
import { API, AuthContext, ThemeContext } from '../App';
import { toast } from 'sonner';

export default function Layout({ children }) {
  const { user } = useContext(AuthContext);
  const { theme, toggleTheme } = useContext(ThemeContext);
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);

  const handleLogout = async () => {
    try {
      await axios.post(`${API}/auth/logout`, {}, { withCredentials: true });
      toast.success('Logged out successfully');
      navigate('/login');
    } catch (error) {
      console.error('Logout error:', error);
      navigate('/login');
    }
  };

  const navItems = [
    { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/portfolio', label: 'Portfolio', icon: Building2 },
    { path: '/simulator', label: 'Simulator', icon: Target },
    { path: '/executive', label: 'Executive', icon: BarChart3 },
  ];

  const isActive = (path) => location.pathname === path;

  return (
    <div className="min-h-screen bg-background">
      {/* Top Navigation */}
      <header className="sticky top-0 z-50 glass border-b border-border">
        <div className="max-w-[1600px] mx-auto px-4 md:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <div 
              className="flex items-center gap-3 cursor-pointer"
              onClick={() => navigate('/dashboard')}
              data-testid="logo"
            >
              <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-400 flex items-center justify-center">
                <Building2 className="w-5 h-5 text-white" />
              </div>
              <div className="hidden sm:block">
                <h1 className="text-lg font-bold tracking-tight">PropTech</h1>
                <p className="text-xs text-blue-400 font-medium -mt-1">Decision Copilot</p>
              </div>
            </div>

            {/* Desktop Navigation */}
            <nav className="hidden md:flex items-center gap-1">
              {navItems.map(({ path, label, icon: Icon }) => (
                <Button
                  key={path}
                  variant="ghost"
                  size="sm"
                  onClick={() => navigate(path)}
                  className={`sidebar-link ${isActive(path) ? 'active bg-zinc-800/50 text-blue-400' : 'text-muted-foreground hover:text-foreground'}`}
                  data-testid={`nav-${label.toLowerCase()}`}
                >
                  <Icon className="w-4 h-4 mr-2" />
                  {label}
                </Button>
              ))}
            </nav>

            {/* Right Side */}
            <div className="flex items-center gap-2">
              {/* Theme Toggle */}
              <Button 
                variant="ghost" 
                size="icon"
                onClick={toggleTheme}
                className="hidden sm:flex"
                data-testid="theme-toggle"
              >
                {theme === 'dark' ? (
                  <Sun className="w-4 h-4" />
                ) : (
                  <Moon className="w-4 h-4" />
                )}
              </Button>

              {/* User Menu */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" className="flex items-center gap-2 p-2" data-testid="user-menu">
                    <Avatar className="h-8 w-8">
                      <AvatarImage src={user?.picture} alt={user?.name} />
                      <AvatarFallback className="bg-blue-500/20 text-blue-400">
                        {user?.name?.charAt(0) || 'U'}
                      </AvatarFallback>
                    </Avatar>
                    <span className="hidden sm:block text-sm font-medium max-w-[120px] truncate">
                      {user?.name}
                    </span>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56 glass">
                  <div className="px-2 py-1.5">
                    <p className="text-sm font-medium">{user?.name}</p>
                    <p className="text-xs text-muted-foreground">{user?.email}</p>
                  </div>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={toggleTheme} className="sm:hidden">
                    {theme === 'dark' ? (
                      <>
                        <Sun className="w-4 h-4 mr-2" />
                        Light Mode
                      </>
                    ) : (
                      <>
                        <Moon className="w-4 h-4 mr-2" />
                        Dark Mode
                      </>
                    )}
                  </DropdownMenuItem>
                  <DropdownMenuItem 
                    onClick={handleLogout}
                    className="text-red-400 focus:text-red-400"
                    data-testid="logout-btn"
                  >
                    <LogOut className="w-4 h-4 mr-2" />
                    Sign Out
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>

              {/* Mobile Menu Button */}
              <Button 
                variant="ghost" 
                size="icon"
                className="md:hidden"
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                data-testid="mobile-menu-btn"
              >
                {mobileMenuOpen ? (
                  <X className="w-5 h-5" />
                ) : (
                  <Menu className="w-5 h-5" />
                )}
              </Button>
            </div>
          </div>

          {/* Mobile Navigation */}
          {mobileMenuOpen && (
            <nav className="md:hidden py-4 border-t border-border">
              <div className="space-y-1">
                {navItems.map(({ path, label, icon: Icon }) => (
                  <Button
                    key={path}
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      navigate(path);
                      setMobileMenuOpen(false);
                    }}
                    className={`w-full justify-start ${isActive(path) ? 'bg-zinc-800/50 text-blue-400' : 'text-muted-foreground'}`}
                  >
                    <Icon className="w-4 h-4 mr-2" />
                    {label}
                  </Button>
                ))}
              </div>
            </nav>
          )}
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-[1600px] mx-auto px-4 md:px-8 py-6">
        {children}
      </main>
    </div>
  );
}
