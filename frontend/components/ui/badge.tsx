import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-xs font-medium transition-colors",
  {
    variants: {
      variant: {
        default: "border-border bg-muted text-foreground",
        pass: "border-teal-600/30 bg-teal-500/10 text-teal-400",
        fail: "border-rose-600/30 bg-rose-500/10 text-rose-400",
        warn: "border-amber-600/30 bg-amber-500/10 text-amber-400",
        info: "border-indigo-600/30 bg-indigo-500/10 text-indigo-400",
        outline: "border-border bg-transparent text-foreground",
        solid: "border-transparent bg-teal-600 text-white",
      },
    },
    defaultVariants: { variant: "default" },
  },
);

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
