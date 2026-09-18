import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Terms & Conditions",
  description: "Terms & Conditions for ExamSentinel.",
};

export default function TermsConditionsPage() {
  return (
    <div className="max-w-4xl mx-auto py-12 px-4 sm:px-6 lg:px-8">
      <div className="bg-white rounded-2xl shadow-sm p-8 sm:p-12 border border-slate-100">
        <h1 className="text-3xl font-bold text-slate-900 mb-6">Terms & Conditions</h1>
        <div className="prose prose-slate max-w-none text-slate-600 space-y-6">
          <p className="text-sm">Last updated: {new Date().toLocaleDateString()}</p>
          
          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-3">1. Agreement to Terms</h2>
            <p>By accessing or using the ExamSentinel platform, you agree to be bound by these Terms and Conditions and our Privacy Policy. If you do not agree to these terms, please do not use our services.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-3">2. Description of Service</h2>
            <p>ExamSentinel provides an online examination platform with proctoring capabilities ("Service"). The Service includes software, web applications, algorithms, and human review processes designed to maintain examination integrity.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-3">3. User Responsibilities</h2>
            <p>As a user of the Service, you agree to:</p>
            <ul className="list-disc pl-5 mt-2 space-y-1">
              <li>Provide accurate and complete registration information.</li>
              <li>Maintain the security of your account credentials.</li>
              <li>Comply with all rules and guidelines established by your educational institution or examining body.</li>
              <li>Not interfere with or disrupt the integrity or performance of the Service.</li>
              <li>Not attempt to gain unauthorized access to the Service or its related systems or networks.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-3">4. Intellectual Property Rights</h2>
            <p>The Service and its original content, features, and functionality are and will remain the exclusive property of ExamSentinel and its licensors. The Service is protected by copyright, trademark, and other laws.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-3">5. Limitation of Liability</h2>
            <p>In no event shall ExamSentinel, nor its directors, employees, partners, agents, suppliers, or affiliates, be liable for any indirect, incidental, special, consequential or punitive damages, including without limitation, loss of profits, data, use, goodwill, or other intangible losses, resulting from your access to or use of or inability to access or use the Service.</p>
          </section>
        </div>
      </div>
    </div>
  );
}
