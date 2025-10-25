import asyncio
import json
import logging
import time

import aioboto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class AsyncS3:
    def __init__(
        self,
        access_key_id,
        secret_access_key,
        bucket_name,
        region_name,
        n_retries=3,
        retry_delay=1.0,
    ):
        self.session = aioboto3.Session(
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region_name,
        )
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.bucket_name = bucket_name
        self.region_name = region_name
        self.n_retries = n_retries
        self.retry_delay = retry_delay

    async def save_file(self, path, data):
        save_start = time.time()
        for attempt in range(1, self.n_retries + 1):
            async with self.session.client(
                "s3",
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                region_name=self.region_name,
            ) as s3:
                try:
                    await s3.put_object(Bucket=self.bucket_name, Key=path, Body=json.dumps(data))
                    duration = time.time() - save_start
                    logger.info(f"✅ DONE to save JSON to S3 | {path} | {duration:.2f}s")
                    return
                except Exception as e:
                    if attempt == self.n_retries:
                        logger.error(f"❌ FAILED to save JSON to S3 | {e}")
                        return
                    else:
                        logger.warning(
                            f"🟡 FAILED to save JSON to S3"
                            f" | attempt {attempt}/{self.n_retries} | {e}"
                        )
                        await asyncio.sleep(self.retry_delay)

    async def load_file(self, path) -> dict | None:
        load_start = time.time()
        for attempt in range(1, self.n_retries + 1):
            try:
                async with self.session.client(
                    "s3",
                    aws_access_key_id=self.access_key_id,
                    aws_secret_access_key=self.secret_access_key,
                    region_name=self.region_name,
                ) as s3:
                    res = await s3.get_object(Bucket=self.bucket_name, Key=path)
                    content = await res["Body"].read()
                    duration = time.time() - load_start
                    logger.info(f"✅ DONE to load JSON from S3 | {path} | {duration:.2f}s")
                    return dict(json.loads(content))
            except ClientError as e:
                if e.response["Error"]["Code"] == "NoSuchKey":
                    logger.info(f"📁 File not found in S3 | {path}")
                    return None
                else:
                    if attempt == self.n_retries:
                        logger.error(f"❌ FAILED to load JSON from S3 | {e}")
                        return None
                    else:
                        logger.warning(
                            f"🟡 FAILED to load JSON from S3"
                            f" | attempt {attempt}/{self.n_retries} | {e}"
                        )
                        await asyncio.sleep(self.retry_delay)
            except Exception as e:
                if attempt == self.n_retries:
                    logger.error(f"❌ FAILED to load JSON from S3 | {e}")
                    return None
                else:
                    logger.warning(
                        f"🟡 FAILED to load JSON from S3"
                        f" | attempt {attempt}/{self.n_retries} | {e}"
                    )
                    await asyncio.sleep(self.retry_delay)
        return None


if __name__ == "__main__":
    import os

    import dotenv

    dotenv.load_dotenv(override=True)

    logging.basicConfig(level=logging.INFO)

    async def main():
        s3 = AsyncS3(
            access_key_id=os.getenv("S3_ACCESS_KEY_ID"),
            secret_access_key=os.getenv("S3_SECRET_ACCESS_KEY"),
            bucket_name=os.getenv("S3_BUCKET"),
            region_name=os.getenv("S3_REGION"),
        )
        await s3.save_file("test.json", {"test": "test"})
        dct = await s3.load_file("test.json")
        print(dct)

    asyncio.run(main())
