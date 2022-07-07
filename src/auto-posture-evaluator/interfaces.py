class TesterInterface:
    def declare_tested_service(self) -> str:
        pass

    def declare_tested_provider(self) -> str:
        pass

    def run_tests(self) -> list:
        pass
