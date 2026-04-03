import logging
import re


SENSITIVE_PATTERN = re.compile(r"(password|token|authorization)=([^\s,;]+)", re.IGNORECASE)


class RedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = SENSITIVE_PATTERN.sub(r"\1=[REDACTED]", record.msg)
        return True


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logging.getLogger().addFilter(RedactionFilter())
