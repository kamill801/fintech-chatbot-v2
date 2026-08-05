/* eslint-disable react-refresh/only-export-components */
import {
  Children,
  createContext,
  isValidElement,
  type AnchorHTMLAttributes,
  type MouseEvent,
  type ReactElement,
  type ReactNode,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

interface LocationState {
  pathname: string;
  search: string;
  hash: string;
}

interface RouterState extends LocationState {
  navigate(to: string | number, options?: { replace?: boolean }): void;
}

const RouterContext = createContext<RouterState | null>(null);
const ParamsContext = createContext<Record<string, string>>({});

function currentLocation(): LocationState {
  return {
    pathname: window.location.pathname,
    search: window.location.search,
    hash: window.location.hash,
  };
}

export function BrowserRouter({ children }: { children: ReactNode }) {
  const [location, setLocation] = useState(currentLocation);

  useEffect(() => {
    const syncLocation = () => setLocation(currentLocation());
    window.addEventListener("popstate", syncLocation);
    return () => window.removeEventListener("popstate", syncLocation);
  }, []);

  const value = useMemo<RouterState>(() => ({
    ...location,
    navigate(to, options) {
      if (typeof to === "number") {
        window.history.go(to);
        return;
      }
      const target = new URL(to, window.location.href);
      const next = `${target.pathname}${target.search}${target.hash}`;
      window.history[options?.replace ? "replaceState" : "pushState"]({}, "", next);
      setLocation(currentLocation());
      window.scrollTo({ top: 0, behavior: "auto" });
    },
  }), [location]);

  return <RouterContext.Provider value={value}>{children}</RouterContext.Provider>;
}

function useRouter(): RouterState {
  const router = useContext(RouterContext);
  if (!router) throw new Error("router components must be inside BrowserRouter");
  return router;
}

export function useLocation(): LocationState {
  const { pathname, search, hash } = useRouter();
  return { pathname, search, hash };
}

export function useNavigate(): RouterState["navigate"] {
  return useRouter().navigate;
}

export function useParams<T extends Record<string, string | undefined> = Record<string, string>>(): T {
  return useContext(ParamsContext) as T;
}

interface LinkProps extends AnchorHTMLAttributes<HTMLAnchorElement> {
  to: string;
}

function shouldHandleLink(event: MouseEvent<HTMLAnchorElement>): boolean {
  return !event.defaultPrevented
    && event.button === 0
    && !event.metaKey
    && !event.ctrlKey
    && !event.shiftKey
    && !event.altKey
    && event.currentTarget.target !== "_blank"
    && !event.currentTarget.hasAttribute("download");
}

export function Link({ to, onClick, ...props }: LinkProps) {
  const navigate = useNavigate();
  return (
    <a
      href={to}
      onClick={(event) => {
        onClick?.(event);
        if (!shouldHandleLink(event)) return;
        event.preventDefault();
        navigate(to);
      }}
      {...props}
    />
  );
}

interface NavLinkProps extends Omit<LinkProps, "className"> {
  className?: string | ((state: { isActive: boolean }) => string);
}

export function NavLink({ className, to, ...props }: NavLinkProps) {
  const { pathname } = useLocation();
  const targetPath = new URL(to, window.location.href).pathname;
  const isActive = targetPath === "/" ? pathname === "/" : pathname === targetPath || pathname.startsWith(`${targetPath}/`);
  const resolvedClass = typeof className === "function" ? className({ isActive }) : className;
  return <Link aria-current={isActive ? "page" : undefined} className={resolvedClass} to={to} {...props} />;
}

interface RouteProps {
  path: string;
  element: ReactElement;
}

export function Route(props: RouteProps): null {
  void props;
  return null;
}

function matchRoute(pattern: string, pathname: string): Record<string, string> | null {
  if (pattern === "*") return {};
  const patternParts = pattern.split("/").filter(Boolean);
  const pathParts = pathname.split("/").filter(Boolean);
  if (patternParts.length !== pathParts.length) return null;
  const params: Record<string, string> = {};
  for (let index = 0; index < patternParts.length; index += 1) {
    const expected = patternParts[index];
    const actual = pathParts[index];
    if (expected.startsWith(":")) params[expected.slice(1)] = decodeURIComponent(actual);
    else if (expected !== actual) return null;
  }
  return params;
}

export function Routes({ children }: { children: ReactNode }) {
  const { pathname } = useLocation();
  for (const child of Children.toArray(children)) {
    if (!isValidElement<RouteProps>(child)) continue;
    const params = matchRoute(child.props.path, pathname);
    if (params !== null) {
      return <ParamsContext.Provider value={params}>{child.props.element}</ParamsContext.Provider>;
    }
  }
  return null;
}

export function Navigate({ to, replace = false }: { to: string; replace?: boolean }) {
  const navigate = useNavigate();
  useEffect(() => navigate(to, { replace }), [navigate, replace, to]);
  return null;
}
