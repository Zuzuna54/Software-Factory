import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
// TODO: Import and configure Redux Provider
// TODO: Import shadcn Toaster for notifications

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
    title: "AI Agent Dashboard",
    description: "Monitoring for the Autonomous AI Team",
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="en">
            <body className={inter.className}>
                {/* <Provider store={store}> */}
                {/* TODO: Add basic layout structure (e.g., sidebar, header) */}
                <main>{children}</main>
                {/* <Toaster /> */}
                {/* </Provider> */}
            </body>
        </html>
    );
}
