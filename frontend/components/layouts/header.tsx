'use client';

import { Bell, LogOut, Settings } from 'lucide-react';
import { useLogout } from '@/lib/api/hooks/use-auth';
import { useAuthStore } from '@/store/auth-store';
import { useHydration } from '@/lib/hooks/use-hydration';
import { GlobalSearch } from '@/components/search/global-search';
import { MobileNav } from '@/components/layouts/mobile-nav';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Skeleton } from '@/components/ui/skeleton';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';

/**
 * Skeleton component shown during hydration to prevent flash
 */
function HeaderSkeleton() {
  return (
    <header className="flex items-center justify-between border-b bg-white px-4 md:px-6 py-4">
      <div className="flex items-center gap-4 flex-1">
        <Skeleton className="h-10 w-10 rounded-md md:hidden" />
        <Skeleton className="h-10 flex-1 max-w-md" />
      </div>
      <div className="flex items-center gap-4">
        <Skeleton className="h-10 w-10 rounded-md" />
        <Skeleton className="h-8 w-8 rounded-full" />
      </div>
    </header>
  );
}

export function Header() {
  const hydrated = useHydration();
  const logoutMutation = useLogout();
  const user = useAuthStore((state) => state.user);

  // Show skeleton during hydration to prevent flash of unauthenticated state
  if (!hydrated) {
    return <HeaderSkeleton />;
  }

  const handleLogout = (): void => {
    logoutMutation.mutate();
  };

  const userInitials = user?.first_name && user?.last_name
    ? `${user.first_name[0]}${user.last_name[0]}`.toUpperCase()
    : user?.email?.[0]?.toUpperCase() || 'U';

  return (
    <header className="flex items-center justify-between border-b bg-white px-4 md:px-6 py-4">
      <div className="flex items-center gap-4 flex-1">
        {/* Mobile hamburger menu */}
        <MobileNav />
        <div className="flex-1 max-w-md">
          <GlobalSearch />
        </div>
      </div>

      <div className="flex items-center gap-2 md:gap-4">
        {/* Notifications Badge */}
        <Button variant="ghost" size="icon" className="relative">
          <Bell className="h-5 w-5" />
          {/* Uncomment when implementing notifications
          <Badge
            variant="destructive"
            className="absolute -top-1 -right-1 h-5 w-5 rounded-full p-0 flex items-center justify-center text-xs"
          >
            3
          </Badge>
          */}
        </Button>

        {/* User Dropdown Menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="flex items-center gap-2 px-2">
              <Avatar className="h-8 w-8">
                <AvatarFallback className="bg-primary text-primary-foreground">
                  {userInitials}
                </AvatarFallback>
              </Avatar>
              <span className="hidden md:inline font-medium">
                {user?.first_name}
              </span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>
              <div className="flex flex-col">
                <div className="font-semibold">
                  {user?.first_name} {user?.last_name}
                </div>
                <div className="text-xs font-normal text-muted-foreground">
                  {user?.email}
                </div>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem>
              <Settings className="mr-2 h-4 w-4" />
              <span>Configurações</span>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={handleLogout}
              className="text-destructive focus:text-destructive focus:bg-destructive/10"
            >
              <LogOut className="mr-2 h-4 w-4" />
              <span>Sair</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
