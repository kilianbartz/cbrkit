import cbrkit
import polars

retriever = cbrkit.retrieval.build(
    cbrkit.sim.attribute_value(
        attributes={
            "year": cbrkit.sim.numbers.linear(max=50),
            "make": cbrkit.sim.strings.levenshtein(),
            "miles": cbrkit.sim.numbers.linear(max=1000000),
        },
        aggregator=cbrkit.sim.aggregator(pooling="mean"),
    ),
    limit=5,
)
df = polars.read_csv("data/cars-1k.csv")
casebase = cbrkit.loaders.polars(df)
for x in casebase:
    print(x)
    break
query = {"year": "2010", "make": "Toyota", "miles": 10000}
print(retriever(casebase, query))
