use csv::Reader;
use distance;

#[derive(Debug)]
struct Record {
    price: i32,
    year: i32,
    manufacturer: String,
    make: String,
    fuel: String,
    miles: i32,
    title_status: String,
    transmission: String,
    drive: String,
    type_: String,
    paint_color: String,
    sim: f64,
}
fn main() {
    // read csv as Record structs
    let start = std::time::Instant::now();
    let mut rdr =
        Reader::from_path(r"C:\Users\kilia\cbrkit\data\cars-10m.csv").expect("Cannot read file");
    let mut records = Vec::new();

    for result in rdr.records() {
        let record = result.expect("Error reading record");
        let record = Record {
            price: record[0].parse().expect("Error parsing price"),
            year: record[1].parse().expect("Error parsing year"),
            manufacturer: record[2].to_string(),
            make: record[3].to_string(),
            fuel: record[4].to_string(),
            miles: record[5].parse().expect("Error parsing miles"),
            title_status: record[6].to_string(),
            transmission: record[7].to_string(),
            drive: record[8].to_string(),
            type_: record[9].to_string(),
            paint_color: record[10].to_string(),
            sim: 0.,
        };
        records.push(record);
    }
    let testmake = "max";
    let testprice = 10000;
    let testmiles = 20000;
    let neg_alpha = -0.01;
    for record in records.iter_mut() {
        let makesim = distance::levenshtein(&record.make, testmake) as f64;
        let makesim = 1.0 - (makesim / record.make.len().max(testmake.len()) as f64);
        let pricesim = ((record.price as f64 - testprice as f64).abs() * neg_alpha).exp();
        let milessim = ((record.miles as f64 - testmiles as f64).abs() * neg_alpha).exp();
        record.sim = (makesim + pricesim + milessim) / 3.0;
    }
    records.sort_by(|a, b| b.sim.partial_cmp(&a.sim).unwrap());
    for record in records.iter().take(20) {
        println!("{:?}", record);
    }
    println!("Time: {:?}", start.elapsed());
}
