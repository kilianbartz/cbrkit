"""
.. include:: ../cli.md
"""

import os
import sys
from pathlib import Path
from typing import Annotated

try:
    import typer
    from rich import print
except ModuleNotFoundError:
    print(
        "Please install cbrkit with the [cli] extra to use the command line interface."
    )
    raise

import cbrkit

app = typer.Typer()


@app.callback()
def app_callback():
    pass


@app.command()
def retrieve(casebase_path: Path, queries_path: Path, retriever: str):
    casebase = cbrkit.loaders.path(casebase_path)
    queries = cbrkit.loaders.path(queries_path)
    retrievers = cbrkit.retrieval.load(retriever)

    for query_name, query in queries.items():
        result = cbrkit.retrieval.apply(casebase, query, retrievers)
        print(f"Query: {query_name}")
        print(result.ranking)
        print()


@app.command()
def serve(
    retriever: list[str],
    search_path: Annotated[list[Path], typer.Option(default_factory=list)],
    reload: bool = False,
) -> None:
    import uvicorn

    sys.path.extend(str(x) for x in search_path)
    os.environ["CBRKIT_RETRIEVER"] = ",".join(retriever)

    uvicorn.run(
        "cbrkit.api:app",
        reload=reload,
    )


if __name__ == "__main__":
    app()
